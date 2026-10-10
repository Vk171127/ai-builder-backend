# Gatekeeper Classifier Model Card

## Summary

- Model: LightGBM multiclass + isotonic calibration (CalibratedClassifierCV)
- Classes (9): bank_official_vishing, bec_vendor, benign, digital_arrest_cbi, digital_arrest_trai, investment_fake_app, kyc_expiry_phishing, remote_access_tech, romance_scam
- Train sessions: 88000
- Validation sessions: 11000
- Validation macro F1: 0.7250

## Per-class metrics (validation)

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| bank_official_vishing | 1.0000 | 0.9565 | 0.9778 | 115 |
| bec_vendor | 0.9057 | 0.7869 | 0.8421 | 122 |
| benign | 1.0000 | 1.0000 | 1.0000 | 10062 |
| digital_arrest_cbi | 0.9537 | 1.0000 | 0.9763 | 103 |
| digital_arrest_trai | 0.6129 | 0.1496 | 0.2405 | 127 |
| investment_fake_app | 0.5444 | 0.7419 | 0.6280 | 124 |
| kyc_expiry_phishing | 0.8188 | 1.0000 | 0.9004 | 122 |
| remote_access_tech | 0.4783 | 0.8919 | 0.6226 | 111 |
| romance_scam | 0.5000 | 0.2544 | 0.3372 | 114 |

## Features

`event_count, high_risk_event_count, velocity_x100, profile_trust_x100, normal_count, suspicious_count, malicious_count, phone_count, extension_count, server_count, new_payee_count, amount_outlier_count, contact_count, trust_building_count, isolation_count, pressure_count, extraction_count, avg_trust_x100, std_trust_x100, suspicious_ratio_x100, malicious_ratio_x100, contact_phone_count, trust_building_extension_count, isolation_extension_count, pressure_phone_count, extraction_server_count`