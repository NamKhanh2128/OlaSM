"""Add Conversational Offer Engine tables.

Revision ID: coe_001_offer_tables
Revises: fc877ccd583a
Create Date: 2026-10-03

Thêm 3 bảng cho Conversational Offer Engine (COE):
  - user_offer_profiles : behavioral profile (ChurnRisk / PriceSensitivity signals)
  - promotions          : promotion catalog với targeting rules
  - promotion_usages    : per-user usage tracking (idempotency + budget control)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "coe_001_offer_tables"
down_revision: str = "fc877ccd583a"
branch_labels = None
depends_on = None

# JSON type that uses JSONB on PostgreSQL for indexing support
JSON_DOCUMENT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    # ── user_offer_profiles ──────────────────────────────────────────────────
    op.create_table(
        "user_offer_profiles",
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),

        # Frequency / Recency
        sa.Column("total_rides", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rides_last_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rides_last_7d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_monthly_rides", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("days_since_last_ride", sa.Integer(), nullable=True),

        # Price sensitivity raw signals
        sa.Column("avg_fare_accepted", BIGINT, nullable=True),
        sa.Column("promo_usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("promo_usage_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cancel_on_high_fare", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downgrade_count", sa.Integer(), nullable=False, server_default="0"),

        # Churn signals
        sa.Column("peak_cancel_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("peak_booking_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_no_ride_days", sa.Integer(), nullable=False, server_default="0"),

        # Behavioral clusters (JSONB arrays)
        sa.Column("frequent_zones", JSON_DOCUMENT, nullable=False, server_default="[]"),
        sa.Column("preferred_hours", JSON_DOCUMENT, nullable=False, server_default="[]"),
        sa.Column("preferred_vehicles", JSON_DOCUMENT, nullable=False, server_default="[]"),
        sa.Column("historical_routes", JSON_DOCUMENT, nullable=False, server_default="[]"),
        sa.Column("loyalty_tier", sa.String(20), nullable=False, server_default="'BRONZE'"),

        # Computed scores (cached; refreshed async after each trip)
        sa.Column("churn_risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("price_sensitivity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_scored_at", sa.DateTime(timezone=True), nullable=True),

        # Audit
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_offer_profiles_churn", "user_offer_profiles", ["churn_risk_score"], postgresql_ops={"churn_risk_score": "DESC"})
    op.create_index("ix_offer_profiles_tier", "user_offer_profiles", ["loyalty_tier"])

    # ── promotions ───────────────────────────────────────────────────────────
    op.create_table(
        "promotions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),

        # Discount definition
        sa.Column("discount_type", sa.String(20), nullable=False),   # PERCENT | FIXED_VND | FREE_RIDE
        sa.Column("discount_value", sa.Integer(), nullable=False),
        sa.Column("max_discount_vnd", sa.Integer(), nullable=True),   # cap for PERCENT type
        sa.Column("min_fare_vnd", sa.Integer(), nullable=False, server_default="0"),

        # Targeting filters (NULL = no filter = match all)
        sa.Column("target_tiers", JSON_DOCUMENT, nullable=True),      # ["SILVER","GOLD"] or null
        sa.Column("valid_vehicle_types", JSON_DOCUMENT, nullable=True),
        sa.Column("valid_hours", JSON_DOCUMENT, nullable=True),        # [7,8,17,18,19]
        sa.Column("valid_zones", JSON_DOCUMENT, nullable=True),
        sa.Column("new_route_only", sa.Boolean(), nullable=False, server_default="false"),

        # Budget & usage control
        sa.Column("total_budget_vnd", BIGINT, nullable=True),
        sa.Column("spent_budget_vnd", BIGINT, nullable=False, server_default="0"),
        sa.Column("usage_per_user", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_usage_limit", sa.Integer(), nullable=True),
        sa.Column("current_usage", sa.Integer(), nullable=False, server_default="0"),

        # Campaign fit weight (business input 0-100)
        sa.Column("campaign_priority", sa.Integer(), nullable=False, server_default="50"),

        # Validity
        sa.Column("status", sa.String(20), nullable=False, server_default="'ACTIVE'"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_promotions_active", "promotions", ["status", "valid_from", "valid_until"])
    op.create_index("ix_promotions_code", "promotions", ["code"])

    # ── promotion_usages ─────────────────────────────────────────────────────
    op.create_table(
        "promotion_usages",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column("promotion_id", sa.String(32), sa.ForeignKey("promotions.id"), nullable=False),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("booking_id", sa.String(32), nullable=True),
        sa.Column("discount_amount", BIGINT, nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("promotion_id", "user_id", "booking_id", name="uq_promo_usage_booking"),
    )
    op.create_index("ix_promo_usage_user", "promotion_usages", ["user_id", "promotion_id"])


def downgrade() -> None:
    op.drop_table("promotion_usages")
    op.drop_index("ix_promotions_code", "promotions")
    op.drop_index("ix_promotions_active", "promotions")
    op.drop_table("promotions")
    op.drop_index("ix_offer_profiles_tier", "user_offer_profiles")
    op.drop_index("ix_offer_profiles_churn", "user_offer_profiles")
    op.drop_table("user_offer_profiles")
