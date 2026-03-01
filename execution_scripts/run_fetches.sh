#!/usr/bin/env fish
cd /home/zombie/D/s/execution_scripts

# Run all fetch scripts
./fetch_finance_crypto.py
./fetch_finance_usstocks.py
./fetch_finance_indstocks.py

# Optional: Log output and errors (uncomment if needed)
# ./fetch_finance_crypto.py >> crypto_fetch.log 2>&1

