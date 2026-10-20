"""The documents the OCR tests read, drawn by the one generator (tools/real_format_documents.py) in the real layouts.

Everything is built for one fixed booking (container CSQU3054383, truck TRK-80579, a hazardous export), plus the
variants the tests need: other goods, an expired or blurry pass, a wrong container, missing details."""

import dataclasses
import shutil
from pathlib import Path

from tools import make_demo_appointments as demo
from tools import real_format_documents as real

BOOKING = dataclasses.replace(
    demo.SCENARIOS[1],
    container="CSQU3054383", truck="TRK-80579", carrier="Carrier-B", seal="SL884213", weight_kg="24,350",
    plate="WP CAB-1234", vessel="MV EVER GRACE", voyage="042E", cargo_category="export",
)


def make_samples(out: Path, appt_date: str, booking=BOOKING) -> Path:
    """The good set (seven documents) and every faulty or incomplete variant, written into `out`."""
    s = booking
    real.booking_confirmation(s, out, "booking_confirmation", appt_date)
    real.cusdec(s, out, "cusdec", appt_date)
    real.gate_pass(s, out, "gate_pass", appt_date)
    real.vgm(s, out, "vgm", appt_date)
    real.seal_report(s, out, "seal_photo", appt_date)
    real.driver_card(s, out, "driver_docs", appt_date)
    real.special_cargo(s, out, "special_cargo", appt_date)

    # other goods, so the customs risk differs
    real.cusdec(dataclasses.replace(s, goods="Cotton T-shirts", hs="6109.10"), out, "cusdec_low_risk", appt_date)
    real.cusdec(dataclasses.replace(s, goods="Cigarettes", hs="2402.20"), out, "cusdec_high_risk", appt_date)
    real.cusdec(s, out, "cusdec_incomplete", appt_date, omit=("declaration_no", "hs_code", "goods"))
    # a delayed vessel
    real.booking_confirmation(dataclasses.replace(s, vessel="MV OCEAN PIONEER", voyage="17W"), out, "booking_confirmation_delayed_vessel", appt_date)
    real.booking_confirmation(s, out, "booking_confirmation_incomplete", appt_date, omit=("voyage", "port_of_discharge", "etd"))
    # faults
    real.vgm(s, out, "vgm_wrong_container", appt_date, container=real.OTHER_CONTAINER)
    real.vgm(s, out, "vgm_bad_weight", appt_date, gross=450)
    real.seal_report(s, out, "seal_missing", appt_date, with_seal=False)
    real.driver_card(s, out, "driver_docs_incomplete", appt_date, complete=False)
    real.gate_pass(s, out, "gate_pass_expired", appt_date, pass_dates=("2019-12-30", "2020-01-01"))
    real.gate_pass(s, out, "_tmp", appt_date)
    real.blur(out / "_tmp.png", out / "gate_pass_blurry.png")
    (out / "_tmp.png").unlink()
    real.special_cargo(s, out, "special_cargo_incomplete", appt_date, omit=("un_number", "packing_group"))
    real.special_cargo(dataclasses.replace(s, container_type="reefer"), out, "special_cargo_reefer", appt_date)
    shutil.copy(out / "booking_confirmation.png", out / "wrong_document.png")  # a booking confirmation in the VGM slot
    return out
