import csv
import io

from app.models.campaign import CampaignLead
from app.services.campaign_csv import build_leads_csv


def test_csv_unions_context_keys_and_keeps_phone_first() -> None:
    leads = [
        CampaignLead(phone_number="+15550001", context={"name": "Ada"}),
        CampaignLead(phone_number="+15550002", context={"city": "Pune", "name": "Grace"}),
    ]
    text = build_leads_csv(leads).decode()
    rows = list(csv.DictReader(io.StringIO(text)))
    assert list(rows[0]) == ["phone_number", "name", "city"]
    assert rows[0]["phone_number"] == "+15550001"
    assert rows[0]["name"] == "Ada"
    assert rows[0]["city"] == ""
    assert rows[1]["city"] == "Pune"
