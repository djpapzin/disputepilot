# Synthetic demo email: Service delivery / billing escalation

> This fixture is synthetic. It does not represent a real person, company, account, service provider, bill, or dispute.

From: support@example-service-demo.test  
To: demo.user@example.test  
Subject: Re: Incorrect billing after cancelled service

Hi,

Thank you for contacting Example Service Demo. We have logged your billing query under reference DP-SVC-204. Our records show the cancellation request was received, but the final invoice may not have been adjusted yet.

Please reply with any missing details by **5 August 2026**. We will escalate to the billing review queue once received.

Kind regards,  
Example Service Demo Support

## Expected extraction

- Case type: service_billing_escalation
- Deadline: 2026-08-05
- Risk: medium
- Suggested action: draft escalation reply with concise timeline and request corrected invoice
