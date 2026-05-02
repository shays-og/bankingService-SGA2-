import grpc
import uuid
import time
from concurrent import futures
from datetime import datetime, timezone

import banking_pb2
import banking_pb2_grpc

accounts = {
    "user_001": 5000.0,
    "user_002": 3000.0,
    "user_003": 1500.0,
}

transaction_history = {
    "user_001": [],
    "user_002": [],
    "user_003": [],
}



class AccountManagementServicer(banking_pb2_grpc.AccountManagementServiceServicer):

    def getBalance(self, request, context):
        """Returns the current balance for a given user_id."""
        user_id = request.user_id


        if user_id not in accounts:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Account not found for user_id: {user_id}")
            return banking_pb2.BalanceResponse()

        return banking_pb2.BalanceResponse(
            user_id=user_id,
            balance=accounts[user_id]
        )

    def updateBalance(self, request, context):
        """Credits or debits a user's account balance."""
        user_id        = request.user_id
        amount         = request.amount
        operation_type = request.operation_type.upper()


        if user_id not in accounts:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Account not found for user_id: {user_id}")
            return banking_pb2.StatusResponse(success=False, message="User not found.")


        if amount <= 0:
            return banking_pb2.StatusResponse(
                success=False,
                message="Amount must be greater than zero."
            )


        if operation_type not in ("CREDIT", "DEBIT"):
            return banking_pb2.StatusResponse(
                success=False,
                message="operation_type must be 'CREDIT' or 'DEBIT'."
            )

        if operation_type == "CREDIT":
            accounts[user_id] += amount
            return banking_pb2.StatusResponse(
                success=True,
                message=f"Credited {amount} to {user_id}. New balance: {accounts[user_id]:.2f}"
            )

        if operation_type == "DEBIT":

            if accounts[user_id] < amount:
                return banking_pb2.StatusResponse(
                    success=False,
                    message=f"Insufficient funds. Available: {accounts[user_id]:.2f}, Requested: {amount:.2f}"
                )
            accounts[user_id] -= amount
            return banking_pb2.StatusResponse(
                success=True,
                message=f"Debited {amount} from {user_id}. New balance: {accounts[user_id]:.2f}"
            )



class TransactionServicer(banking_pb2_grpc.TransactionServiceServicer):

    def initiateTransfer(self, request, context):
        """Transfers money from sender to receiver."""
        sender_id   = request.sender_id
        receiver_id = request.receiver_id
        amount      = request.amount
        note        = request.note


        if sender_id not in accounts:
            return banking_pb2.TransferResponse(
                success=False,
                transaction_id="",
                message=f"Sender account not found: {sender_id}"
            )


        if receiver_id not in accounts:
            return banking_pb2.TransferResponse(
                success=False,
                transaction_id="",
                message=f"Receiver account not found: {receiver_id}"
            )


        if amount <= 0:
            return banking_pb2.TransferResponse(
                success=False,
                transaction_id="",
                message="Transfer amount must be greater than zero."
            )


        if sender_id == receiver_id:
            return banking_pb2.TransferResponse(
                success=False,
                transaction_id="",
                message="Sender and receiver cannot be the same account."
            )


        if accounts[sender_id] < amount:
            return banking_pb2.TransferResponse(
                success=False,
                transaction_id="",
                message=f"Insufficient funds. Available: {accounts[sender_id]:.2f}, Requested: {amount:.2f}"
            )


        accounts[sender_id]   -= amount
        accounts[receiver_id] += amount


        txn_id    = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        txn = banking_pb2.Transaction(
            transaction_id=txn_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            amount=amount,
            status="SUCCESS",
            timestamp=timestamp,
            note=note
        )


        transaction_history.setdefault(sender_id, []).append(txn)
        transaction_history.setdefault(receiver_id, []).append(txn)

        return banking_pb2.TransferResponse(
            success=True,
            transaction_id=txn_id,
            message=f"Transfer of {amount:.2f} from {sender_id} to {receiver_id} successful."
        )

    def getTransactionHistory(self, request, context):
        """Returns paginated transaction history for a user."""
        user_id  = request.user_id
        page     = request.page     if request.page     > 0 else 1
        per_page = request.per_page if request.per_page > 0 else 10


        if user_id not in accounts:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Account not found for user_id: {user_id}")
            return banking_pb2.TransactionHistoryResponse()

        all_txns    = transaction_history.get(user_id, [])
        total_count = len(all_txns)


        start = (page - 1) * per_page
        end   = start + per_page
        page_txns = all_txns[start:end]

        return banking_pb2.TransactionHistoryResponse(
            transactions=page_txns,
            total_count=total_count
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    banking_pb2_grpc.add_AccountManagementServiceServicer_to_server(
        AccountManagementServicer(), server
    )
    banking_pb2_grpc.add_TransactionServiceServicer_to_server(
        TransactionServicer(), server
    )

    server.add_insecure_port("[::]:50051")
    server.start()
    print("=" * 50)
    print("  Banking gRPC Server started on port 50051")
    print("=" * 50)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
