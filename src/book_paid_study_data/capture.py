"""Capture Prolific's public participant terms through the shared lake runtime."""

import argparse
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from .cli import resource, validate
from .observability import init_sentry, report_exit


class Text(HTMLParser):
    """Extract visible page text while ignoring executable content."""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


REQUIRED_MARKERS = {
    "prolific-participants-how-it-works": (
        "join the waitlist",
        "when you're eligible for a study, it will appear on your dashboard",
        "once you've earned $/£6 in a given currency",
        "minimum payment threshold",
        "data collectors are required to pay participants at least £6.00/$8.00 per hour",
        "data privacy",
        "prolific id",
    ),
    "respondent-paid-research-participants": (
        "getting paid for research studies",
        "one-on-one interviews",
        "surveys",
    ),
    "usertesting-paid-contributors": (
        "get paid to test",
        "practice test",
        "surveys",
    ),
    "yougov-panel-surveys": (
        "our panel",
        "members are paid",
        "surveys",
    ),
    "nih-research-participant-compensation": (
        "compensation for research participation",
        "research participants",
        "payment",
    ),
}


GENERIC_SOURCES = {
    "respondent-paid-research-participants": {
        "study_method": "One-on-one interviews, focus groups, surveys and other remote or in-person research studies.",
        "eligibility_text": "Respondent participants create an account and complete unpaid screeners; researchers decide whom to invite and each study has its own criteria.",
        "consent": "Review each researcher's consent and privacy notice before sharing information; no screener answers or participant account data are stored here.",
    },
    "usertesting-paid-contributors": {
        "study_method": "Recorded usability tests, surveys and live conversations about products and experiences.",
        "eligibility_text": "UserTesting participants apply, complete a practice test and answer screening questions; approval and each test's criteria are separate.",
        "consent": "The public participant flow describes screen, audio, video or conversation tests; review the contributor terms and each test's consent before participating.",
    },
    "yougov-panel-surveys": {
        "study_method": "Online surveys and other opt-in data-sharing activities through the YouGov panel.",
        "eligibility_text": "YouGov panel membership and survey invitations depend on country, profile and current panel rules; no invitation is guaranteed by this capture.",
        "consent": "Review YouGov's panel promise, privacy terms and each survey's data-use notice before participating.",
    },
    "nih-research-participant-compensation": {
        "study_method": "Academic and medical research participation with compensation governed by study and institutional review rules.",
        "eligibility_text": "The NIH page explains how compensation for research participation is governed; it is not an enrollment listing, and each study has its own eligibility and consent process.",
        "consent": "Research participation requires study-specific informed consent and institutional review; no health information or study response is collected here.",
    },
}


def normalize(raw, source, checked_at):
    """Turn the public participant page into one conservative platform record."""
    if source["id"] not in REQUIRED_MARKERS:
        raise ValueError("unknown paid-study source")
    parser = Text()
    parser.feed(raw.decode("utf-8"))
    # The public page uses typographic apostrophes in some releases; fold them
    # so drift checks distinguish wording changes from harmless HTML typography.
    text = " ".join(" ".join(parser.parts).split()).replace("’", "'")
    folded = text.casefold()
    required = REQUIRED_MARKERS[source["id"]]
    if not all(marker.casefold() in folded for marker in required):
        raise ValueError("paid-study source drift or challenge page")

    # The page documents a platform or participation policy, not a guaranteed
    # inventory of studies. Availability therefore remains unknown instead of
    # implying that a reader will receive an invitation or a payout.
    if source["id"] == "prolific-participants-how-it-works":
        item = {
            "id": source["id"],
            "title": "Prolific participant studies",
            "category": source["category"],
            "source_url": source["source_url"],
            "provider": source["provider"],
            "status": "unknown",
            "deadline": {"kind": "unknown", "at": None},
            "eligible_countries": [],
            "eligibility_text": (
                "Join the waitlist, verify the account and review each study's own "
                "eligibility filters. Supported countries, study qualification and "
                "invitation timing are not established by this capture."
            ),
            "value": {
                "kind": "variable",
                "amount": None,
                "currency": None,
                "guaranteed": False,
            },
            "cost": {
                "fee_amount": None,
                "currency": None,
                "auto_renewal": None,
                "notes": (
                    "The page describes participant rewards and cash-out terms but "
                    "does not establish that every account or study has zero cost."
                ),
            },
            "terms": {
                "study_method": (
                    "Online research studies, surveys, questionnaires, decision games "
                    "and AI or product evaluation tasks; participation is opt-in."
                ),
                "duration_minutes": None,
                "screening_required": True,
                "consent_and_data_use": (
                    "Prolific says data is stored securely and data collectors see a "
                    "Prolific ID; any personally identifiable information request is "
                    "disclosed up front and optional. Review each study's consent "
                    "before participating."
                ),
            },
            "related_records": [],
            "provenance": {
                "evidence_kind": "captured",
                "source_id": source["id"],
                "source_record_id": source["id"],
                "checked_at": checked_at,
                "raw_object_key": None,
                "bronze_manifest_key": None,
            },
        }
    else:
        metadata = GENERIC_SOURCES[source["id"]]
        item = {
            "id": source["id"],
            "title": source["title"],
            "category": source["category"],
            "source_url": source["source_url"],
            "provider": source["provider"],
            "status": "unknown",
            "deadline": {"kind": "unknown", "at": None},
            "eligible_countries": [],
            "eligibility_text": metadata["eligibility_text"],
            "value": {
                "kind": "cash" if source["category"] in {"user-interview", "usability-test"} else "variable",
                "amount": None,
                "currency": None,
                "guaranteed": False,
            },
            "cost": {
                "fee_amount": None,
                "currency": None,
                "auto_renewal": None,
                "notes": source["cost_notes"],
            },
            "terms": {
                "study_method": metadata["study_method"],
                "duration_minutes": None,
                "screening_required": True,
                "consent_and_data_use": metadata["consent"],
            },
            "related_records": [],
            "provenance": {
                "evidence_kind": "captured",
                "source_id": source["id"],
                "source_record_id": source["id"],
                "checked_at": checked_at,
                "raw_object_key": None,
                "bronze_manifest_key": None,
            },
        }
    return {
        "schema_version": source["schema_version"],
        "source": source["product"],
        "retrieved_at": checked_at,
        "data_status": "live",
        "items": [item],
    }


def source_config(source_id=None):
    if source_id is None:
        return resource("source.json")
    if not re.fullmatch(r"[a-z0-9-]+", source_id):
        raise ValueError("invalid source id")
    base = resource("source.json")
    if base["id"] == source_id:
        return base
    try:
        return resource("source-" + source_id + ".json")
    except FileNotFoundError:
        raise ValueError("unknown source id") from None


def main(argv=None):
    selector = argparse.ArgumentParser(add_help=False)
    selector.add_argument("--source-id")
    selected, remaining = selector.parse_known_args(argv)
    root = os.environ.get("SOLO_DATA_LAKE_ROOT")
    if not root:
        print("Set SOLO_DATA_LAKE_ROOT to the local shared capture/lake runtime.", file=sys.stderr)
        return 2
    runtime = Path(root).resolve() / "infra/scripts"
    if not (runtime / "discovery/capture_runtime.py").is_file():
        print("Shared discovery runtime is unavailable.", file=sys.stderr)
        return 2
    sys.path.insert(0, str(runtime))
    from discovery.capture_runtime import VERSION, run

    if VERSION != 1:
        raise RuntimeError("unsupported shared capture runtime")
    source = source_config(selected.source_id)
    sentry = init_sentry(source["id"])
    return report_exit(sentry, source["id"], run(source, normalize, validate, remaining))


if __name__ == "__main__":
    raise SystemExit(main())
