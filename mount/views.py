from urllib import request

import django
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Detail,Account,Transaction,DataPurchase
from decouple import config
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .form import DetailForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
FLW_SECRET_HASH = config("FLW_SECRET_HASH")
FLW_SECRET_KEY = config("FLW_SECRET_KEY")
@login_required
def home(request):
    if request.method == "POST":
        form = DetailForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('success')
    else:
        form = DetailForm()

    return render(request, 'home.html', {'form': form})
def success(request):
    return render(request, 'success.html')

def payment(request):
    return render(request, 'payment.html')

def report(request):
    return render(request, 'report.html')


from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages

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
from django.shortcuts import render

from .form import DetailForm
from django.contrib.auth.decorators import login_required

from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

@api_view(['POST'])
def api_login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)

    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})
    return Response({"error": "Invalid credentials"}, status=400)

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from .models import Detail
from .serializers import DetailSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    detail, _ = Detail.objects.get_or_create(user=request.user)
    serializer = DetailSerializer(detail)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    detail, _ = Detail.objects.get_or_create(user=request.user)

    serializer = DetailSerializer(detail, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=400)


from decimal import Decimal
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Account

@api_view(['POST'])
def deposit(request):

    account_number = request.data.get('account_number')
    amount = request.data.get('amount')

    try:
        account = Account.objects.get(account_number=account_number)

    except Account.DoesNotExist:
        return Response({
            "error": "Account not found"
        }, status=404)

    account.balance += Decimal(amount)
    account.save()

    return Response({
        "message": "Deposit successful",
        "new_balance": account.balance
    })
from decimal import Decimal
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Account

@api_view(['POST'])
def withdraw(request):

    account_number = request.data.get('account_number')
    amount = request.data.get('amount')

    if not account_number or not amount:
        return Response({
            "error": "account_number and amount required"
        }, status=400)

    try:
        account = Account.objects.get(account_number=account_number)

    except Account.DoesNotExist:
        return Response({
            "error": "Account not found"
        }, status=404)

    try:
        amount = Decimal(amount)

    except:
        return Response({
            "error": "Invalid amount"
        }, status=400)

    if amount > account.balance:
        return Response({
            "error": "Insufficient balance"
        }, status=400)

    account.balance -= amount
    account.save()

    return Response({
        "message": "Withdrawal successful",
        "new_balance": account.balance
    })


@api_view(['POST'])
def transfer(request):
    sender_no = request.data['sender']
    receiver_no = request.data['receiver']
    amount = float(request.data['amount'])

    sender = Account.objects.get(account_number=sender_no)
    receiver = Account.objects.get(account_number=receiver_no)

    if sender.balance < amount:
        return Response({"error": "Insufficient funds"})

    sender.balance -= amount
    receiver.balance += amount

    sender.save()
    receiver.save()

    Transaction.objects.create(
        account=sender,
        amount=amount,
        transaction_type='transfer'
    )

    return Response({"message": "Transfer successful"})


def deposit_page(request):
    return render(request, 'payment.html')

import requests
from django.shortcuts import redirect

def initialize_payment(request):
    url = "https://api.paystack.co/transaction/initialize"

    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "email": request.user.email,
        "amount": 5000 * 100  # kobo (₦50 = 5000)
    }

    response = requests.post(url, json=data, headers=headers)
    res_data = response.json()

    return redirect(res_data['data']['authorization_url'])


def verify_payment(request):
    reference = request.GET.get('reference')

    url = f"https://api.paystack.co/transaction/verify/{reference}"

    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
    }

    response = requests.get(url, headers=headers)
    res_data = response.json()

    if res_data['data']['status'] == 'success':
        amount = res_data['data']['amount'] / 100

        account = Account.objects.get(user=request.user)
        account.balance += amount
        account.save()

        Transaction.objects.create(
            user=request.user,
            account=account,
            amount=amount,
            transaction_type='deposit'
        )

        return redirect('success')
    

def send_money(request):
    if request.method == "POST":
        bank_code = request.POST.get("bank_code")
        account_number = request.POST.get("account_number")
        amount = float(request.POST.get("amount"))

        sender = Account.objects.get(user=request.user)

        if sender.balance >= amount:
            sender.balance -= amount
            sender.save()

            # Here is where Flutterwave/Paystack API goes
            print(bank_code, account_number, amount)

            return redirect('success')
        else:
            return render(request, 'send.html', {'error': 'Insufficient balance'})

    return render(request, 'send.html')

def create_recipient(name, account_number, bank_code):
    url = "https://api.paystack.co/transferrecipient"

    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "type": "nuban",
        "name": name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "NGN"
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()

import uuid

def send_money(amount, recipient_code):
    url = "https://api.paystack.co/transfer"
    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "source": "balance",
        "amount": int(amount * 100),
        "recipient": recipient_code,
        "reason": "Transfer from my app"
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()



def transfer(request):
    if request.method == "POST":
        account_number = request.POST.get("account_number")
        bank_code = request.POST.get("bank_code")
        amount = float(request.POST.get("amount"))

        sender = Account.objects.get(user=request.user)

        if sender.balance < amount:
            return render(request, "payment.html", {"error": "Insufficient balance"})

        # 1. Create recipient
        recipient = create_recipient("Customer", account_number, bank_code)

        if not recipient['status']:
            return render(request, "payment.html", {"error": "Recipient error"})

        recipient_code = recipient['data']['recipient_code']

        # 2. Send money
        transfer = send_money(amount, recipient_code)

        if transfer['status']:
            sender.balance -= amount
            sender.save()

            Transaction.objects.create(
                user=request.user,
                account=sender,
                amount=amount,
                transaction_type='transfer'
            )

            return redirect("success")

        return render(request, "payment.html", {"error": "Transfer failed"})

    return render(request, "payment.html")



@csrf_exempt
def flutterwave_webhook(request):

    print(request.body)

    return HttpResponse(status=200)

from decouple import config
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def flutterwave_webhook(request):

    FLW_SECRET_HASH = config('FLW_SECRET_HASH')

    signature = request.headers.get('verif-hash')

    if signature != FLW_SECRET_HASH:
        return HttpResponse(status=401)

    payload = json.loads(request.body)

    print(payload)

    return HttpResponse(status=200)
@login_required
def transaction(request):
    if request.method == "POST":

        account = Account.objects.get(user=request.user)

        amount = Decimal(request.POST.get("amount"))
        tx_type = request.POST.get("transaction_type")

        if tx_type == "deposit":
            account.balance += amount

        elif tx_type == "withdraw":
            if account.balance < amount:
                return redirect("home")
            account.balance -= amount

        account.save()

        Transaction.objects.create(
            user=request.user,
            account=account,
            amount=amount,
            transaction_type=tx_type,
            status="successful"
        )

        return redirect("home")

    return redirect("home")

from decimal import Decimal
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import Account, Transaction


@login_required
def transaction(request):

    if request.method == "POST":

        # CREATE ACCOUNT IF IT DOESN'T EXIST
        account, created = Account.objects.get_or_create(
            user=request.user
        )

        amount = Decimal(request.POST.get("amount"))
        tx_type = request.POST.get("transaction_type")

        # DEPOSIT
        if tx_type == "deposit":
            account.balance += amount

        # WITHDRAW
        elif tx_type == "withdraw":

            if account.balance < amount:
                return redirect("home")

            account.balance -= amount

        # SAVE ACCOUNT
        account.save()

        # SAVE TRANSACTION
        Transaction.objects.create(
            user=request.user,
            account=account,
            amount=amount,
            transaction_type=tx_type,
            status="successful"
        )

        return redirect("success")

    return redirect("success")


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import DataPurchase, Account


@login_required
def buy_data(request):
    if request.method == "POST":

        network = request.POST.get("network")
        phone = request.POST.get("phone_number")
        amount = Decimal(request.POST.get("amount"))

        account = Account.objects.get(user=request.user)

        # check balance
        if account.balance < amount:
            return redirect("home")

        # deduct money
        account.balance -= amount
        account.save()

        # save purchase
        DataPurchase.objects.create(
            user=request.user,
            network=network,
            phone_number=phone,
            amount=amount,
            status="successful"
        )

        return redirect("success")

    return redirect("home")

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Account, Detail, Transaction
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Account, Detail, Transaction

@csrf_exempt
def flutterwave_webhook(request):

    print("WEBHOOK HIT")

    print(request.body)

    return HttpResponse(status=200)