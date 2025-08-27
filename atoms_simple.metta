; Simple MeTTa Knowledge Base for Lightning USSD System

; User definitions with phone numbers and balances (in satoshis)
(User Alice "+254712345678")
(User Bob "+254787654321")
(User Charlie "+254798765432")

; Balance facts
(Balance "+254712345678" 100000)
(Balance "+254787654321" 50000)
(Balance "+254798765432" 75000)

; Transaction history
(Transaction "+254712345678" "+254787654321" 20000)
(Transaction "+254787654321" "+254798765432" 15000)

; System limits
(MinAmount 1000)
(MaxAmount 1000000)
(DailyLimit 5000000)

; Exchange rates (KES to sats: 150 KES = 1000 sats)
(ExchangeRate 150 1000)

; User preferences
(Language "+254712345678" "en")
(Language "+254787654321" "sw")
(Language "+254798765432" "en")

; KYC status
(KYC "+254712345678" verified)
(KYC "+254787654321" pending)
(KYC "+254798765432" verified)

; Activity tracking
(Activity "+254712345678" login)
(Activity "+254787654321" payment)
(Activity "+254798765432" invoice)