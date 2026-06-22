"""Rich intent taxonomy per sector with atomic failure modes and expected behaviors."""

FINITECH_INTENTS = [
    {
        "id": "kyc_verification_status",
        "name": "KYC Verification Status",
        "description": "User asking about KYC approval time, rejection reason, document upload issues",
        "failure_modes": [
            "stuck_pending_longer_than_expected",
            "rejected_without_clear_reason",
            "documents_upload_fails_repeatedly",
            "kyc_shows_pending_after_submission_confirmation",
        ],
        "expected_agent_behavior": [
            "verify_current_kyc_status",
            "explain_rejection_reason_clearly",
            "provide_document_specifications",
            "offer_escalation_if_exceeds_tat",
        ],
    },
    {
        "id": "order_execution_delay",
        "name": "Order Execution Delay",
        "description": "Order not executing, pending longer than usual, slippage complaints",
        "failure_modes": [
            "limit_order_not_filling_at_stated_price",
            "market_order_executed_at_unexpected_price",
            "order_pending_for_minutes_during_volatility",
            "slippage_beyond_expected_range",
        ],
        "expected_agent_behavior": [
            "check_order_status_with_order_id",
            "explain_ltp_vs_limit_order_mechanism",
            "acknowledge_slippage_and_offer_compensation_check",
            "escalate_to_rms_if_abnormal",
        ],
    },
    {
        "id": "withdrawal_failure",
        "name": "Withdrawal Failed / Stuck",
        "description": "Money withdrawal not processing, stuck for 24+ hours, reversed without notification",
        "failure_modes": [
            "withdrawal_stuck_longer_than_stated_tat",
            "withdrawal_reversed_without_explanation",
            "bank_account_not_credited_days_after_confirmation",
            "withdrawal_limit_unexpectedly_low",
        ],
        "expected_agent_behavior": [
            "trace_withdrawal_with_txn_id",
            "explain_reversal_reason_or_bank_processing_time",
            "offer_manual_escalation_to_banking_team",
            "provide_alternative_withdrawal_method",
        ],
    },
    {
        "id": "chart_data_staleness",
        "name": "Chart / Data Staleness",
        "description": "Price charts not updating, wrong historical data, missing timeframes",
        "failure_modes": [
            "intraday_charts_not_updating_in_real_time",
            "historical_data_missing_for_certain_periods",
            "timeframe_options_not_available",
            "chart_indicators_incorrect_or_missing",
        ],
        "expected_agent_behavior": [
            "acknowledge_data_issue_without_blaming_user",
            "check_if_known_technical_issue",
            "provide_alternative_viewing_method",
            "escalate_to_tech_team_with_screenshot",
        ],
    },
    {
        "id": "gtt_order_failure",
        "name": "GTT / Trigger Order Failure",
        "description": "GTT not triggering despite price hitting trigger, GTT creation errors",
        "failure_modes": [
            "gtt_not_triggered_when_price_hit_trigger",
            "gtt_creation_rejected_without_reason",
            "gtt_expired_without_notification",
            "gtt_triggered_at_wrong_price",
        ],
        "expected_agent_behavior": [
            "verify_trigger_price_and_ltp_at_trigger_time",
            "explain_gtt_mechanism_limitations",
            "check_for_any_modifications_after_gtt_setup",
            "offer_manual_order_if_eligible",
        ],
    },
    {
        "id": "margin_shortfall_warning",
        "name": "Margin Shortfall / RMS Squared Off",
        "description": "Position squared off due to margin shortfall, margin requirement not communicated",
        "failure_modes": [
            "position_squared_off_without_adequate_warning",
            "margin_requirement_changed_mid_session",
            "margin_calculation_discrepancy",
            "insufficient_margin_notification_came_too_late",
        ],
        "expected_agent_behavior": [
            "explain_margin_calculation_for_that_position",
            "provide_margin_requirement_timeline",
            "offer_reimbursement_check_if_unfair_square_off",
            "educate_on_margin_monitoring_tools",
        ],
    },
    {
        "id": "fraud_dispute_initiation",
        "name": "Fraud / Unauthorized Transaction Dispute",
        "description": "Unauthorized transaction, account compromised, phishing victim",
        "failure_modes": [
            "unauthorized_txn_debited_from_account",
            "account_login_from_unknown_device",
            "phishing_link_sent_to_user_by_fake_support",
            "fraud_dispute_closed_without_resolution",
        ],
        "expected_agent_behavior": [
            "immediately_lock_account_if_suspected_compromise",
            "initiate_fraud_dispute_with_txn_details",
            "explain_dispute_timeline_and_expectations",
            "provide_safety_guidelines_to_prevent_recurrence",
        ],
    },
    {
        "id": "dp_charges_explanation",
        "name": "DP Charges / Hidden Fees",
        "description": "Confused about demat charges, annual maintenance fee, hidden transaction costs",
        "failure_modes": [
            "dp_charges_deducted_without_notification",
            "annual_maintenance_fee_higher_than_advertised",
            "brokerage_calculation_discrepancy",
            "unexpected_tax_levied_on_transaction",
        ],
        "expected_agent_behavior": [
            "itemize_charges_with_amounts_and_reasons",
            "reference_published_fee_schedule",
            "explain_regulatory_requirements_for_charges",
            "offer_plan_downgrade_if_applicable",
        ],
    },
    {
        "id": "ipo_allotment_status",
        "name": "IPO Allotment / Refund Status",
        "description": "IPO not allotted, refund not received, UPI mandate stuck",
        "failure_modes": [
            "ipo_not_allotted_despite_high_chances",
            "ipo_refund_not_credited_post_non_allotment",
            "upi_mandate_blocked_amount_not_released",
            "ipo_application_status_not_updated",
        ],
        "expected_agent_behavior": [
            "check_ipo_allotment_status_with_pan",
            "explain_refund_timeline_via_upi_or_bank",
            "initiate_mandate_release_if_unblock_needed",
            "escalate_to_ipo_team_if_delayed_beyond_tat",
        ],
    },
    {
        "id": "pledged_stock_unavailability",
        "name": "Pledged Stock / Collateral Issue",
        "description": "Pledged shares not visible, collateral margin not updated, pledge release failure",
        "failure_modes": [
            "pledged_shares_not_showing_in_portfolio",
            "collateral_margin_not_updated_after_pledge",
            "pledge_release_request_stuck",
            "pledge_rejected_due_to_internal_policy_change",
        ],
        "expected_agent_behavior": [
            "verify_pledge_status_with_dp",
            "explain_collateral_margin_calculation",
            "initiate_pledge_release_manually_if_needed",
            "provide_pledge_policy_document_reference",
        ],
    },
    {
        "id": "account_locked_or_restricted",
        "name": "Account Locked / Restricted",
        "description": "Account unexpectedly locked, trading restricted, login blocked",
        "failure_modes": [
            "account_locked_after_multiple_login_attempts",
            "trading_restricted_without_notification",
            "account_flagged_for_kyc_expiry",
            "login_blocked_on_new_device",
        ],
        "expected_agent_behavior": [
            "identify_lock_reason_from_account_flags",
            "guide_through_unlock_process_step_by_step",
            "provide_eima_or_document_requirements",
            "escalate_if_manual_unlock_needed",
        ],
    },
    {
        "id": "notification_missing",
        "name": "Missing Notifications / Alerts",
        "description": "Order confirmation not received, price alert not triggered, SMS/email missing",
        "failure_modes": [
            "order_confirmation_notification_not_received",
            "price_alert_did_not_trigger",
            "sms_not_received_for_otp_or_confirmation",
            "email_notifications_stopped_working",
        ],
        "expected_agent_behavior": [
            "check_notification_settings_for_user",
            "verify_if_notification_was_sent_but_not_delivered",
            "provide_alternative_notification_channel",
            "escalate_to_tech_team_if_systemic",
        ],
    },
    {
        "id": "referral_or_reward_dispute",
        "name": "Referral / Cashback / Reward Dispute",
        "description": "Referral bonus not credited, cashback not applied, reward points missing",
        "failure_modes": [
            "referral_bonus_not_credited_after_valid_referral",
            "cashback_offer_terms_not_honored",
            "reward_points_expired_without_notice",
            "referral_tracking_not_working",
        ],
        "expected_agent_behavior": [
            "verify_referral_tracking_with_referral_code",
            "check_cashback_eligibility_criteria",
            "explain_reward_expiry_policy",
            "offer_manual_credit_if_system_error_confirmed",
        ],
    },
    {
        "id": "mutual_fund_switch_or_redemption",
        "name": "MF Switch / Redemption Delay",
        "description": "Mutual fund redemption not processed, switch order delayed, exit load confusion",
        "failure_modes": [
            "redemption_amount_not_credited_by_expected_date",
            "switch_order_executed_at_wrong_nav",
            "exit_load_applied_incorrectly",
            "fund_scheme_change_not_reflected",
        ],
        "expected_agent_behavior": [
            "check_redemption_status_with_amc",
            "explain_nav_application_for_switch",
            "verify_exit_load_calculation",
            "escalate_to_mf_team_if_beyond_tat",
        ],
    },
    {
        "id": "tax_report_generation",
        "name": "Tax Statement / Report Issues",
        "description": "Capital gains statement not available, tax report wrong, P&L mismatch",
        "failure_modes": [
            "capital_gains_statement_unavailable_for_previous_year",
            "tax_report_shows_incorrect_holdings_period",
            "pnl_statement_mismatch_with_actual_trades",
            "annual_tax_statement_download_fails",
        ],
        "expected_agent_behavior": [
            "verify_report_generation_status",
            "explain_tax_report_data_sources",
            "provide_manual_calculation_if_report_unavailable",
            "escalate_to_reports_team_for_regeneration",
        ],
    },
]

INSURTECH_INTENTS = [
    {
        "id": "claim_status",
        "name": "Claim Status / Delay",
        "description": "Claim not processed, stuck for days, documents requested repeatedly",
        "failure_modes": [
            "claim_stuck_pending_days_beyond_tat",
            "documents_requested_multiple_times",
            "claim_rejected_without_clear_reason",
            "claim_amount_different_from_expectation",
        ],
        "expected_agent_behavior": [
            "provide_claim_tracking_id_and_status",
            "explain_rejection_reason_with_policy_clause",
            "itemize_claim_breakdown",
            "offer_review_or_ombudsman_escalation",
        ],
    },
    {
        "id": "policy_renewal_reminder",
        "name": "Policy Renewal / Lapse",
        "description": "Policy lapsed without reminder, renewal premium changed unexpectedly",
        "failure_modes": [
            "policy_lapsed_without_adequate_reminder",
            "renewal_premium_higher_than_expected",
            "auto_renewal_debited_without_consent",
            "renewal_benefits_changed_from_original",
        ],
        "expected_agent_behavior": [
            "explain_lapse_grace_period_if_applicable",
            "itemize_renewal_premium_breakdown",
            "offer_alternative_plans_or_riders",
            "process_reinstatement_if_eligible",
        ],
    },
    {
        "id": "coverage_dispute",
        "name": "Coverage / Exclusion Dispute",
        "description": "Claim denied due to exclusion not explained at purchase, coverage misinterpretation",
        "failure_modes": [
            "claim_denied_due_to_exclusion_not_disclosed",
            "coverage_amount_less_than_expected",
            "specific_disease_or_event_not_covered",
            "policy_wording_ambiguous_on_coverage",
        ],
        "expected_agent_behavior": [
            "cite_exact_policy_clause_for_exclusion",
            "explain_coverage_limits_with_examples",
            "offer_policy_upgrade_if_available",
            "provide_ombudsman_option_if_disagreement",
        ],
    },
    {
        "id": "premium_payment_failure",
        "name": "Premium Payment Failure",
        "description": "Payment declined, auto-debit failed, payment not reflecting",
        "failure_modes": [
            "payment_declined_despite_sufficient_balance",
            "auto_debit_failed_without_notification",
            "premium_paid_but_not_reflecting_in_policy",
            "payment_gateway_error_during_payment",
        ],
        "expected_agent_behavior": [
            "verify_payment_with_txn_id",
            "explain_bank_or_gateway_delay_if_applicable",
            "provide_alternative_payment_method",
            "offer_grace_period_extension_for_tech_glitch",
        ],
    },
    {
        "id": "nominee_update",
        "name": "Nominee / Beneficiary Update",
        "description": "Nominee change not reflecting, beneficiary details wrong",
        "failure_modes": [
            "nominee_update_stuck_in_processing",
            "nominee_change_rejected_without_reason",
            "multiple_nominee_percentage_split_not_accepted",
            "minor_nominee_guardian_details_issue",
        ],
        "expected_agent_behavior": [
            "explain_nominee_update_process_and_tat",
            "provide_correct_form_or_document_requirements",
            "check_for_pending_nominee_updates",
            "escalate_if_update_exceeds_tat",
        ],
    },
]

SECTOR_TAXONOMIES = {
    "fintech": FINITECH_INTENTS,
    "insurtech": INSURTECH_INTENTS,
}


def get_intents_for_sector(sector_name: str, profile_intents: list[str] | None = None) -> list[dict]:
    """Get taxonomy intents for a sector, optionally filtered by profile intents."""
    tax = SECTOR_TAXONOMIES.get(sector_name, [])
    if not profile_intents:
        return tax
    # Try to match, but fall back to ALL if no matches
    profile_lower = [i.lower() for i in profile_intents]
    matched = []
    for t in tax:
        name_parts = t["name"].lower()
        desc_parts = t["description"].lower()
        search_space = name_parts + " " + desc_parts
        if any(p in search_space or search_space in p for p in profile_lower):
            matched.append(t)
        elif any(kw in search_space for p in profile_lower for kw in p.split() if len(kw) > 3):
            matched.append(t)
    return matched if matched else tax
