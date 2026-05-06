from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse

def signup(request):
    if request.method == "POST": 
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('login')

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully")
        return redirect('login')

    return render(request, 'signup.html')

from django.contrib.auth import authenticate, login

def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'login.html')

from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('login')

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from decimal import Decimal, InvalidOperation
import json
import requests
import logging

from decouple import config

from .models import Account, Transaction, Detail, DataPurchase
from .serializers import DetailSerializer

logger = logging.getLogger(__name__)


# =========================
# HELPERS
# =========================

def get_or_create_account(user):
    account, _ = Account.objects.get_or_create(user=user)
    return account


def flw_headers():
    return {"Authorization": f"Bearer {settings.FLW_SECRET_KEY}"}


def verify_flw_transaction(transaction_id):
    """Call Flutterwave's verify endpoint and return parsed data or None."""
    try:
        response = requests.get(
            f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
            headers=flw_headers(),
            timeout=10,
        )
        data = response.json()
        if data.get("status") == "success":
            return data.get("data")
    except requests.RequestException as e:
        logger.error(f"Flutterwave verify error: {e}")
    return None


def credit_account(transaction_obj):
    """Credit account for a transaction — idempotent (checks status first)."""
    if transaction_obj.status == "successful":
        return False  # already processed
    transaction_obj.status = "successful"
    transaction_obj.save()
    account = transaction_obj.account
    account.balance += transaction_obj.amount
    account.save()
    return True


# =========================
# AUTH (WEB)
# =========================

def signup(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect("signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "That username is already taken.")
            return redirect("signup")

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Account created! Please log in.")
        return redirect("login")

    return render(request, "signup.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("home")

        messages.error(request, "Invalid username or password.")
        return redirect("login")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# =========================
# WEB PAGES
# =========================

@login_required
def home(request):
    account = get_or_create_account(request.user)
    recent_transactions = Transaction.objects.filter(
        user=request.user
    ).order_by("-created_at")[:5]
    context = {
        "account": account,
        "recent_transactions": recent_transactions,
    }
    return render(request, "home.html", context)


@login_required
def payment(request):
    account = get_or_create_account(request.user)
    return render(request, "payment.html", {"account": account})


@login_required
def report(request):
    transactions = Transaction.objects.filter(user=request.user).order_by("-created_at")
    data_purchases = DataPurchase.objects.filter(user=request.user).order_by("-created_at")
    context = {
        "transactions": transactions,
        "data_purchases": data_purchases,
    }
    return render(request, "report.html", context)


@login_required
def success(request):
    return render(request, "success.html")


@login_required
def succed_data(request):
    return render(request, "succed_data.html")


@login_required
def succed_trans(request):
    return render(request, "succed_trans.html")


def low_balance(request):
    return render(request, "low_balance.html")


# =========================
# PROFILE (DRF)
# =========================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile(request):
    detail, _ = Detail.objects.get_or_create(user=request.user)
    serializer = DetailSerializer(detail)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    detail, _ = Detail.objects.get_or_create(user=request.user)
    serializer = DetailSerializer(detail, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


# =========================
# AUTH API
# =========================

@api_view(["POST"])
def api_login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)

    if not user:
        return Response({"error": "Invalid credentials"}, status=400)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key})


# =========================
# WALLET OPERATIONS (API)
# =========================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw(request):
    account_number = request.data.get("account_number")
    amount_raw = request.data.get("amount")

    if not account_number or not amount_raw:
        return Response({"error": "account_number and amount are required."}, status=400)

    try:
        account = Account.objects.get(account_number=account_number)
        amount = Decimal(str(amount_raw))
    except (Account.DoesNotExist, InvalidOperation):
        return Response({"error": "Invalid account number or amount."}, status=400)

    if amount <= 0:
        return Response({"error": "Amount must be positive."}, status=400)

    if account.balance < amount:
        return Response({"error": "Insufficient balance."}, status=400)

    account.balance -= amount
    account.save()

    Transaction.objects.create(
        user=account.user,
        account=account,
        amount=amount,
        transaction_type="withdraw",
        status="successful",
    )

    return Response({"message": "Withdrawal successful.", "balance": str(account.balance)})


# =========================
# DEPOSIT (WEB)
# =========================

@login_required
def deposit(request):
    """
    Renders deposit page on GET.
    On POST, creates a pending Transaction and redirects to Flutterwave.
    """
    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get("amount", "0"))
        except InvalidOperation:
            messages.error(request, "Invalid amount.")
            return redirect("deposit")

        if amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("deposit")

        account = get_or_create_account(request.user)

        transaction = Transaction.objects.create(
            user=request.user,
            account=account,
            amount=amount,
            transaction_type="deposit",
            status="pending",
        )

        payload = {
            "tx_ref": transaction.reference,
            "amount": str(amount),
            "currency": "NGN",
            "redirect_url": request.build_absolute_uri("/payment-success/"),
            "customer": {
                "email": request.user.email or f"{request.user.username}@placeholder.com",
                "name": request.user.get_full_name() or request.user.username,
            },
            "customizations": {
                "title": "Wallet Deposit",
                "description": f"Deposit ₦{amount} into your wallet",
            },
        }

        try:
            response = requests.post(
                "https://api.flutterwave.com/v3/payments",
                json=payload,
                headers=flw_headers(),
                timeout=10,
            )
            response_data = response.json()
        except requests.RequestException as e:
            logger.error(f"Flutterwave initiation error: {e}")
            transaction.status = "failed"
            transaction.save()
            messages.error(request, "Could not connect to payment provider. Please try again.")
            return redirect("deposit")

        if response_data.get("status") == "success":
            payment_link = response_data["data"]["link"]
            return redirect(payment_link)

        # Flutterwave returned an error
        logger.error(f"Flutterwave error response: {response_data}")
        transaction.status = "failed"
        transaction.save()
        messages.error(request, "Payment initiation failed. Please try again.")
        return redirect("deposit")

    return render(request, "deposit.html")


# =========================
# PAYMENT SUCCESS (Flutterwave redirect)
# =========================

@login_required
def payment_success(request):
    """
    Flutterwave redirects here after the user completes (or cancels) payment.
    We re-verify with Flutterwave before crediting the account.
    """
    status = request.GET.get("status")
    tx_ref = request.GET.get("tx_ref")
    transaction_id = request.GET.get("transaction_id")

    if status != "successful" or not transaction_id or not tx_ref:
        messages.error(request, "Payment was not completed.")
        return redirect("home")

    # Verify with Flutterwave
    flw_data = verify_flw_transaction(transaction_id)

    if not flw_data or flw_data.get("status") != "successful":
        messages.error(request, "Payment could not be verified. Contact support if funds were debited.")
        return redirect("home")

    # Match to our Transaction record
    try:
        transaction = Transaction.objects.get(reference=tx_ref)
    except Transaction.DoesNotExist:
        messages.error(request, "Transaction record not found.")
        return redirect("home")

    # Ensure the verified amount matches what we recorded (fraud check)
    flw_amount = Decimal(str(flw_data.get("amount", 0)))
    if flw_amount < transaction.amount:
        logger.warning(
            f"Amount mismatch: expected {transaction.amount}, got {flw_amount} for tx_ref={tx_ref}"
        )
        messages.error(request, "Payment amount mismatch. Please contact support.")
        return redirect("home")

    credited = credit_account(transaction)
    if credited:
        messages.success(request, f"₦{transaction.amount:,} has been added to your wallet.")
    else:
        messages.info(request, "This payment was already processed.")

    return redirect("success")


# =========================
# WITHDRAW (WEB)
# =========================

@login_required
def transaction(request):
    """
    Handles both deposit and withdraw from a single form.
    Deposit → Flutterwave. Withdraw → direct balance deduction.
    """
    if request.method == "POST":
        tx_type = request.POST.get("transaction_type")

        if tx_type == "deposit":
            # Delegate to the deposit view logic
            return deposit(request)

        elif tx_type == "withdraw":
            try:
                amount = Decimal(request.POST.get("amount", "0"))
            except InvalidOperation:
                messages.error(request, "Invalid amount.")
                return redirect("home")

            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect("home")

            account = get_or_create_account(request.user)

            if account.balance < amount:
                messages.error(request, "Insufficient balance.")
                return redirect("low_balance")

            account.balance -= amount
            account.save()

            Transaction.objects.create(
                user=request.user,
                account=account,
                amount=amount,
                transaction_type="withdraw",
                status="successful",
            )

            messages.success(request, f"₦{amount:,} successfully withdrawn.")
            return redirect("succed_trans")

    return redirect("home")


# =========================
# TRANSFER (WEB)
# =========================

@login_required
def transfer(request):
    if request.method == "POST":
        receiver_no = request.POST.get("receiver", "").strip()
        try:
            amount = Decimal(request.POST.get("amount", "0"))
        except InvalidOperation:
            messages.error(request, "Invalid amount.")
            return redirect("transfer")

        if amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("transfer")

        sender = get_or_create_account(request.user)

        try:
            receiver = Account.objects.get(account_number=receiver_no)
        except Account.DoesNotExist:
            messages.error(request, "Recipient account not found.")
            return redirect("transfer")

        if receiver.user == request.user:
            messages.error(request, "You cannot transfer to your own account.")
            return redirect("transfer")

        if sender.balance < amount:
            messages.error(request, "Insufficient balance.")
            return redirect("low_balance")

        # Atomic-ish transfer
        sender.balance -= amount
        receiver.balance += amount
        sender.save()
        receiver.save()

        Transaction.objects.create(
            user=request.user,
            account=sender,
            amount=amount,
            transaction_type="transfer",
            status="successful",
        )

        messages.success(request, f"₦{amount:,} transferred successfully.")
        return redirect("success")

    return render(request, "transfer.html")


# =========================
# DATA PURCHASE (WEB)
# =========================

@login_required
def buy_data(request):
    if request.method == "POST":
        network = request.POST.get("network", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        amount_raw = request.POST.get("amount", "0")

        if not network or not phone:
            messages.error(request, "Network and phone number are required.")
            return redirect("buy_data")

        try:
            amount = Decimal(amount_raw)
        except InvalidOperation:
            messages.error(request, "Invalid amount.")
            return redirect("buy_data")

        if amount <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("buy_data")

        try:
            account = Account.objects.get(user=request.user)
        except Account.DoesNotExist:
            messages.error(request, "Wallet account not found.")
            return redirect("home")

        if account.balance < amount:
            return redirect("low_balance")

        account.balance -= amount
        account.save()

        DataPurchase.objects.create(
            user=request.user,
            network=network,
            phone_number=phone,
            amount=amount,
            status="successful",
        )

        messages.success(request, f"{network} data purchased for {phone}.")
        return redirect("succed_data")

    return render(request, "buy_data.html")


# =========================
# FLUTTERWAVE WEBHOOK
# =========================

@csrf_exempt
def flutterwave_webhook(request):
    """
    Server-to-server event from Flutterwave.
    Secured with a shared secret hash (set FLW_WEBHOOK_SECRET in .env).
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    # Verify the webhook secret
    secret_hash = config("FLW_WEBHOOK_SECRET", default="")
    signature = request.headers.get("verif-hash", "")

    if secret_hash and signature != secret_hash:
        logger.warning("Flutterwave webhook: invalid signature.")
        return JsonResponse({"error": "Unauthorized."}, status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    event = payload.get("event")

    if event == "charge.completed":
        data = payload.get("data", {})

        if data.get("status") == "successful":
            tx_ref = data.get("tx_ref")

            try:
                transaction = Transaction.objects.get(reference=tx_ref)
            except Transaction.DoesNotExist:
                logger.error(f"Webhook: transaction not found for tx_ref={tx_ref}")
                return JsonResponse({"status": "ok"})  # Return 200 so FLW stops retrying

            credited = credit_account(transaction)
            if credited:
                logger.info(f"Webhook: credited ₦{transaction.amount} for tx_ref={tx_ref}")
            else:
                logger.info(f"Webhook: tx_ref={tx_ref} already processed.")

    return JsonResponse({"status": "ok"})


from django.shortcuts import render, redirect
from django.contrib import messages

def report_view(request):
    if request.method == 'POST':
        message = request.POST.get('message')

        print(message)  # debug

        # TODO: save to DB if needed

        messages.success(request, 'Report sent!')
        return redirect('report')

    return render(request, 'report.html')
from .models import Report

Report.objects.create(message=messages)


