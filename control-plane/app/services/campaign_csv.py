import csv
import io

from app.models.campaign import CampaignLead


def build_leads_csv(leads: list[CampaignLead]) -> bytes:
    """phone_number is required by Dograh's campaign source validator; every
    other column becomes {{initial_context.<column>}} in the workflow, so
    the header set is the union of every lead's context keys."""

    context_keys: list[str] = []
    seen = set()
    for lead in leads:
        for key in lead.context:
            if key not in seen:
                seen.add(key)
                context_keys.append(key)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["phone_number", *context_keys])
    writer.writeheader()
    for lead in leads:
        writer.writerow({"phone_number": lead.phone_number, **lead.context})

    return buffer.getvalue().encode("utf-8")
