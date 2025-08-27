; MeTTa Knowledge Base for Lightning USSD System

; User definitions with phone numbers and balances (in satoshis)
(User Alice "+254712345678" 100000)
(User Bob "+254787654321" 50000)
(User Charlie "+254798765432" 75000)

; Balance facts
(Balance "+254712345678" 100000)
(Balance "+254787654321" 50000)
(Balance "+254798765432" 75000)

; Transaction history
(Transaction "+254712345678" "+254787654321" 20000 Lightning "2025-08-23T10:30:00Z")
(Transaction "+254787654321" "+254798765432" 15000 Lightning "2025-08-23T11:15:00Z")

; USSD State definitions
(State MainMenu (Options 
    (1 "Send BTC")
    (2 "Receive BTC") 
    (3 "Send Invoice")
    (4 "Top Up via M-Pesa")
    (5 "Withdraw to M-Pesa")
    (0 "Exit")
))

(State SendBTC (RequiredInputs phone_number amount))
(State ReceiveBTC (RequiredInputs amount memo))
(State SendInvoice (RequiredInputs phone_number amount memo))
(State TopUp (RequiredInputs amount mpesa_code))
(State Withdraw (RequiredInputs amount mpesa_number))

; Business rules
(Rule InsufficientFunds 
    (If (< (Balance $user) $amount)
        (Error "Insufficient balance")))

(Rule ValidPhoneNumber
    (If (not (StartsWith $phone "+254"))
        (Error "Invalid phone number format")))

(Rule MinimumAmount
    (If (< $amount 1000)
        (Error "Minimum amount is 1000 sats")))

(Rule MaximumAmount
    (If (> $amount 1000000)
        (Error "Maximum amount is 1,000,000 sats")))

; Exchange rates (KES to sats)
(ExchangeRate KES 150 1000)  ; 150 KES = 1000 sats

; Convert KES to sats
(ConvertToSats $kes_amount (* $kes_amount (/ 1000 150)))

; Convert sats to KES  
(ConvertToKES $sats_amount (* $sats_amount (/ 150 1000)))

; Invoice templates
(InvoiceTemplate 
    "Lightning Invoice: {amount} sats\nFrom: {sender}\nMemo: {memo}\nPay with: {payment_request}")

(SMSTemplate
    "USSD Bitcoin: {message}")

; Transaction validation
(ValidateTransaction $from $to $amount
    (And 
        (ValidPhoneNumber $from)
        (ValidPhoneNumber $to)
        (MinimumAmount $amount)
        (MaximumAmount $amount)
        (>= (Balance $from) $amount)))

; Update balance after successful transaction
(UpdateBalance $user $amount_change
    (Let $current_balance (Balance $user)
         $new_balance (+ $current_balance $amount_change)
         (Balance $user $new_balance)))

; Fee calculation (1% for Lightning transactions)
(CalculateFee $amount (* $amount 0.01))

; System limits
(DailyLimit 5000000)  ; 5M sats per day
(TransactionLimit 1000000)  ; 1M sats per transaction

; User preferences
(Preference "+254712345678" Language "en")
(Preference "+254787654321" Language "sw")  ; Swahili
(Preference "+254798765432" Language "en")

; Error messages in multiple languages
(ErrorMsg "insufficient_funds" "en" "Insufficient balance")
(ErrorMsg "insufficient_funds" "sw" "Salio haitoshi")
(ErrorMsg "invalid_phone" "en" "Invalid phone number")
(ErrorMsg "invalid_phone" "sw" "Nambari ya simu si sahihi")

; Success messages
(SuccessMsg "payment_sent" "en" "Payment sent successfully")
(SuccessMsg "payment_sent" "sw" "Malipo yamefanywa kikamilifu")

; Menu translations
(MenuText "main_menu" "en" "Bitcoin Lightning\n1. Send BTC\n2. Receive BTC\n3. Send Invoice\n4. Top Up M-Pesa\n5. Withdraw M-Pesa\n0. Exit")
(MenuText "main_menu" "sw" "Bitcoin Lightning\n1. Tuma BTC\n2. Pokea BTC\n3. Tuma Ankara\n4. Ingiza M-Pesa\n5. Toa M-Pesa\n0. Ondoka")

; Activity tracking
(Activity "+254712345678" "login" "2025-08-23T10:00:00Z")
(Activity "+254712345678" "send_btc" "2025-08-23T10:30:00Z")
(Activity "+254787654321" "receive_btc" "2025-08-23T10:30:00Z")

; KYC status
(KYCStatus "+254712345678" verified)
(KYCStatus "+254787654321" pending)
(KYCStatus "+254798765432" verified)

; Transaction limits based on KYC
(GetTransactionLimit $user
    (If (= (KYCStatus $user) verified)
        1000000
        100000))