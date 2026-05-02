import grpc
import banking_pb2
import banking_pb2_grpc


# ─────────────────────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────────────────────

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

def divider():
    print("-" * 55)


# ─────────────────────────────────────────────────────────────
# ACCOUNT MANAGEMENT CLIENT CALLS
# ─────────────────────────────────────────────────────────────

def check_balance(stub, user_id):
    """Fetch and display balance for a user."""
    print(f"\n[getBalance] Checking balance for: {user_id}")
    try:
        response = stub.getBalance(banking_pb2.BalanceRequest(user_id=user_id))
        print(f"  -> User: {response.user_id} | Balance: ₹{response.balance:.2f}")
    except grpc.RpcError as e:
        print(f"  -> ERROR: {e.code()} - {e.details()}")


def update_balance(stub, user_id, amount, operation_type):
    """Credit or debit a user's account."""
    print(f"\n[updateBalance] {operation_type} ₹{amount:.2f} for {user_id}")
    response = stub.updateBalance(banking_pb2.UpdateBalanceRequest(
        user_id=user_id,
        amount=amount,
        operation_type=operation_type
    ))
    status = "SUCCESS" if response.success else "FAILED"
    print(f"  -> [{status}] {response.message}")


# ─────────────────────────────────────────────────────────────
# TRANSACTION CLIENT CALLS
# ─────────────────────────────────────────────────────────────

def initiate_transfer(stub, sender_id, receiver_id, amount, note=""):
    """Transfer money between two accounts."""
    print(f"\n[initiateTransfer] ₹{amount:.2f} from {sender_id} to {receiver_id}")
    response = stub.initiateTransfer(banking_pb2.TransferRequest(
        sender_id=sender_id,
        receiver_id=receiver_id,
        amount=amount,
        note=note
    ))
    status = "SUCCESS" if response.success else "FAILED"
    print(f"  -> [{status}] {response.message}")
    if response.transaction_id:
        print(f"  -> Transaction ID: {response.transaction_id}")


def get_transaction_history(stub, user_id, page=1, per_page=10):
    """Fetch and display paginated transaction history."""
    print(f"\n[getTransactionHistory] History for {user_id} (page {page})")
    try:
        response = stub.getTransactionHistory(banking_pb2.TransactionHistoryRequest(
            user_id=user_id,
            page=page,
            per_page=per_page
        ))
        print(f"  -> Total Transactions: {response.total_count}")
        if not response.transactions:
            print("  -> No transactions found.")
        for txn in response.transactions:
            print(f"     [{txn.timestamp}] ID: {txn.transaction_id[:8]}...")
            print(f"       {txn.sender_id} -> {txn.receiver_id} | ₹{txn.amount:.2f} | {txn.status}")
            if txn.note:
                print(f"       Note: {txn.note}")
    except grpc.RpcError as e:
        print(f"  -> ERROR: {e.code()} - {e.details()}")


# ─────────────────────────────────────────────────────────────
# AUTOMATED TEST SUITE
# ─────────────────────────────────────────────────────────────

def run_tests(account_stub, txn_stub):
    section("TEST 1: Check Initial Balances")
    check_balance(account_stub, "user_001")
    check_balance(account_stub, "user_002")
    check_balance(account_stub, "user_003")

    section("TEST 2: Non-Existing User (Error Handling)")
    check_balance(account_stub, "user_999")

    section("TEST 3: Update Balance (Credit & Debit)")
    update_balance(account_stub, "user_001", 1000.0, "CREDIT")
    update_balance(account_stub, "user_002", 500.0,  "DEBIT")
    check_balance(account_stub, "user_001")
    check_balance(account_stub, "user_002")

    section("TEST 4: Insufficient Funds (Error Handling)")
    update_balance(account_stub, "user_003", 99999.0, "DEBIT")

    section("TEST 5: Successful Money Transfer")
    initiate_transfer(txn_stub, "user_001", "user_002", 200.0, note="Rent payment")
    check_balance(account_stub, "user_001")
    check_balance(account_stub, "user_002")

    section("TEST 6: Transfer - Insufficient Funds (Error Handling)")
    initiate_transfer(txn_stub, "user_003", "user_001", 50000.0, note="Should fail")

    section("TEST 7: Transfer to Non-Existing User (Error Handling)")
    initiate_transfer(txn_stub, "user_001", "user_999", 100.0)

    section("TEST 8: Multiple Transfers + Transaction History")
    initiate_transfer(txn_stub, "user_002", "user_003", 100.0, note="Loan repayment")
    initiate_transfer(txn_stub, "user_001", "user_003", 50.0,  note="Shared expense")
    get_transaction_history(txn_stub, "user_001")
    get_transaction_history(txn_stub, "user_002")
    get_transaction_history(txn_stub, "user_003")

    section("TEST 9: History for Non-Existing User (Error Handling)")
    get_transaction_history(txn_stub, "user_999")

    print(f"\n{'='*55}")
    print("  All 9 tests completed.")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────
# INTERACTIVE MENU HANDLERS
# ─────────────────────────────────────────────────────────────

def menu_check_balance(account_stub):
    print("\n-- Check Balance --")
    user_id = input("  Enter User ID: ").strip()
    if not user_id:
        print("  User ID cannot be empty.")
        return
    check_balance(account_stub, user_id)


def menu_update_balance(account_stub):
    print("\n-- Update Balance --")
    user_id = input("  Enter User ID: ").strip()
    if not user_id:
        print("  User ID cannot be empty.")
        return

    amount_str = input("  Enter Amount: ").strip()
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        print("  Invalid amount. Must be a positive number.")
        return

    op = input("  Operation (CREDIT / DEBIT): ").strip().upper()
    if op not in ("CREDIT", "DEBIT"):
        print("  Invalid operation. Must be CREDIT or DEBIT.")
        return

    update_balance(account_stub, user_id, amount, op)


def menu_initiate_transfer(txn_stub):
    print("\n-- Initiate Transfer --")
    sender_id = input("  Enter Sender User ID: ").strip()
    if not sender_id:
        print("  Sender ID cannot be empty.")
        return

    receiver_id = input("  Enter Receiver User ID: ").strip()
    if not receiver_id:
        print("  Receiver ID cannot be empty.")
        return

    amount_str = input("  Enter Amount: ").strip()
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        print("  Invalid amount. Must be a positive number.")
        return

    note = input("  Enter Note (optional, press Enter to skip): ").strip()
    initiate_transfer(txn_stub, sender_id, receiver_id, amount, note)


def menu_transaction_history(txn_stub):
    print("\n-- Transaction History --")
    user_id = input("  Enter User ID: ").strip()
    if not user_id:
        print("  User ID cannot be empty.")
        return

    page_str     = input("  Page number (default 1): ").strip()
    per_page_str = input("  Results per page (default 10): ").strip()

    page     = int(page_str)     if page_str.isdigit()     else 1
    per_page = int(per_page_str) if per_page_str.isdigit() else 10

    get_transaction_history(txn_stub, user_id, page, per_page)


# ─────────────────────────────────────────────────────────────
# INTERACTIVE MENU LOOP
# ─────────────────────────────────────────────────────────────

def run_interactive(account_stub, txn_stub):
    section("Interactive Banking Client")
    print("  Connected to gRPC server on localhost:50051")
    print("  Pre-seeded accounts: user_001, user_002, user_003\n")

    menu = """
    1. Check Balance                       
    2. Update Balance (Credit / Debit)     
    3. Initiate Transfer                   
    4. View Transaction History            
    5. Run Automated Test Suite            
    0. Exit"""

    while True:
        print(menu)
        choice = input("  Enter your choice: ").strip()

        if choice == "1":
            menu_check_balance(account_stub)

        elif choice == "2":
            menu_update_balance(account_stub)

        elif choice == "3":
            menu_initiate_transfer(txn_stub)

        elif choice == "4":
            menu_transaction_history(txn_stub)

        elif choice == "5":
            section("Running Automated Test Suite")
            run_tests(account_stub, txn_stub)

        elif choice == "0":
            print("\n  Goodbye!\n")
            break

        else:
            print("\n  Invalid choice. Please enter a number from the menu.")

        input("\n  Press Enter to continue...")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    channel      = grpc.insecure_channel("localhost:50051")
    account_stub = banking_pb2_grpc.AccountManagementServiceStub(channel)
    txn_stub     = banking_pb2_grpc.TransactionServiceStub(channel)

    run_interactive(account_stub, txn_stub)
