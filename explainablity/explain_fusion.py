def explain_fusion(z_lstm, z_if, z_social):
    return {
        "lstm_contribution": z_lstm * 1.8,
        "if_contribution": z_if * 1.2,
        "social_contribution": z_social * 1.0
    }
