# Etsy API Credentials Guide

Complete guide to get your Etsy API credentials for AutoLister.

---

## Prerequisites

- An Etsy account (free to create)
- An Etsy shop (required for selling)
- Web browser
- Ability to receive SMS or use 2FA app (for security)

---

## Step 1: Create or Log into Etsy Account

1. Go to [https://www.etsy.com](https://www.etsy.com)
2. Click "Register" if you don't have an account
3. Or log in with your existing account

---

## Step 2: Create Your Etsy Shop

### 2.1 Open Shop Settings

1. Click on your profile icon (top right)
2. Select "Sell on Etsy"
3. Click "Open your Etsy shop"

### 2.2 Fill in Shop Information

**Shop Name** (Choose carefully - see recommendations below)
- Must be unique
- 4-20 characters
- No spaces (use underscores or hyphens)
- Examples: `ManualsHub`, `EquipmentDocs`, `TechManuals`

**Language**: English

**Country/Region**: Your location

**Currency**: USD (recommended)

### 2.3 Complete Shop Setup

Follow the prompts to:
- Set up payment method
- Add shop policies
- Add shop announcement (optional)
- Upload shop banner (optional)

**Note**: You may need to list your first item manually to fully activate the shop.

---

## Step 3: Get Your Shop ID

### 3.1 Navigate to Shop Settings

1. Go to [Etsy.com](https://www.etsy.com)
2. Click "You" (top right)
3. Click "Shop Manager"
4. Click "Settings" (left sidebar)
5. Click "Info & Appearance"

### 3.2 Find Your Shop ID

Your Shop ID is displayed in two places:

**Option A**: In the URL
```
https://www.etsy.com/shop/YOUR_SHOP_NAME/about
```

The number after `/shop/` is your shop name, not the ID.

**Option B**: In the page content
- Look for "Shop ID: 123456789" in the page
- Or check the page source for the ID

### 3.3 Copy Your Shop ID

Copy the numeric Shop ID (e.g., `123456789`) - you'll need this for the `.env` file.

---

## Step 4: Create Etsy Developer App

### 4.1 Go to Etsy Developers

1. Go to [https://www.etsy.com/developers](https://www.etsy.com/developers)
2. Click "Create an App" button

### 4.2 Fill in App Details

**App Name**: 
- Use a descriptive name
- Example: `AutoLister` or `ManualsBot`

**App Description**:
- Describe what the app does
- Example: `Automated tool for listing equipment manuals`

**App URL**:
- This is where your AutoLister dashboard will be
- If running on Raspberry Pi: `http://YOUR_PI_IP:8000`
- Example: `http://192.168.5.8:8000`
- You can use a placeholder if not sure: `http://localhost:8000`

**Callback URL**:
- Same as App URL
- Example: `http://YOUR_PI_IP:8000`

**Email**:
- Your contact email

### 4.3 Request Permissions

You need these permissions for AutoLister:

**Required Permissions**:
- ✅ `listings_r` - Read listings (needed to view your listings)
- ✅ `listings_w` - Write listings (needed to create listings)
- ✅ `listings_d` - Delete listings (needed to remove listings)

**Optional** (not needed for basic functionality):
- `transactions_r` - Read transactions
- `billing_r` - Read billing

### 4.4 Create the App

1. Click "Create App" button
2. Review the terms and conditions
3. Click "Accept" if you agree

---

## Step 5: Get Your API Credentials

### 5.1 Copy API Key and Shared Secret

After creating the app, you'll see:

**API Keystring** (example format):
```
your_api_key_here
```

**Shared Secret** (example format):
```
your_shared_secret_here
```

**Copy both of these** - you'll need them for the `.env` file.

### 5.2 Generate Access Tokens

### Option A: Generate via Etsy Dashboard

1. On the app page, click "Generate Token"
2. Review the permissions being requested
3. Click "Allow Access"
4. You'll receive:
   - **Access Token**
   - **Access Token Secret**

### Option B: Generate via OAuth Flow (Advanced)

If you need to generate tokens programmatically:

1. Use the OAuth 2.0 flow
2. Redirect user to Etsy's authorization URL
3. User approves permissions
4. Receive authorization code
5. Exchange code for access token

**For AutoLister, Option A is recommended.**

---

## Step 6: Configure AutoLister with Credentials

### 6.1 Edit the .env File

On your Raspberry Pi:

```bash
cd ~/AutoLister
nano .env
```

### 6.2 Add Your Etsy Credentials

Add these lines to your `.env` file:

```env
# Etsy API Configuration
ETSY_API_KEY=your_actual_api_key_here
ETSY_API_SECRET=your_actual_shared_secret_here
ETSY_ACCESS_TOKEN=your_actual_access_token_here
ETSY_ACCESS_TOKEN_SECRET=your_actual_access_token_secret_here
ETSY_SHOP_ID=your_actual_shop_id_here
ETSY_DEFAULT_PRICE=4.99
ETSY_DEFAULT_QUANTITY=9999
```

### 6.3 Save and Exit

Press `Ctrl+X`, then `Y`, then `Enter` to save and exit.

---

## Step 7: Verify Credentials

### 7.1 Restart AutoLister

```bash
cd ~/AutoLister/docker
docker-compose restart autolister
```

### 7.2 Check Logs for Errors

```bash
docker-compose logs autolister
```

Look for authentication errors in the logs.

### 7.3 Test Etsy Connection

```bash
# Access the Python shell in the container
docker exec -it autolister python

# Test the connection
from app.etsy import EtsyClient
client = EtsyClient()
print(client.test_connection())
```

Should return: `True`

---

## Important Notes

### Token Expiration

- **Access tokens do not expire** unless revoked
- You can revoke tokens from your Etsy account settings
- If you revoke a token, you'll need to generate a new one

### Security Best Practices

1. **Never commit credentials to git**
   - The `.env` file is in `.gitignore`
   - Always use `.env.example` as a template

2. **Use separate tokens for development and production**
   - Create a separate Etsy app for testing
   - Use different tokens for different environments

3. **Monitor API usage**
   - Etsy has rate limits
   - Check your API usage in the developer dashboard

4. **Keep credentials secure**
   - Only share with trusted team members
   - Rotate tokens periodically

### Rate Limits

Etsy API has rate limits:
- **10,000 requests per day** for most endpoints
- AutoLister is designed to respect these limits
- If you hit limits, the app will wait and retry

---

## Troubleshooting

### Issue: "Invalid API Key" Error

**Solution**: 
- Double-check the API key in `.env`
- Ensure no extra spaces or quotes
- Regenerate the key if needed

### Issue: "Shop Not Found" Error

**Solution**:
- Verify your Shop ID is correct
- Check that your shop is active (not suspended)
- Ensure you have at least one listing in your shop

### Issue: "Unauthorized" Error

**Solution**:
- Verify access token and secret are correct
- Check that tokens haven't been revoked
- Regenerate tokens if needed

### Issue: "Insufficient Permissions" Error

**Solution**:
- Ensure you requested all required permissions
- Re-authorize the app with correct permissions
- Check that your Etsy account is in good standing

---

## Etsy Shop Name Recommendations

### Good Names:
- `ManualsHub`
- `EquipmentManuals`
- `ServiceManualsDirect`
- `ManualMaster`
- `TechManuals`
- `EquipmentDocs`
- `RepairManuals`
- `ManualLibrary`
- `DigitalManuals`
- `ManualsArchive`

### Avoid:
- Brand names (e.g., "HondaManuals", "YamahaDocs")
- Trademarked terms
- Very long names
- Names with spaces (use underscores or hyphens)
- Numbers-only names

### Tips:
- Keep it under 20 characters
- Make it memorable
- Indicate what you sell
- Use professional language
- Check availability before creating

---

## Additional Resources

- [Etsy Developers Documentation](https://www.etsy.com/developers/documentation)
- [Etsy API Reference](https://openapi.etsy.com/v3)
- [Etsy Seller Handbook](https://www.etsy.com/seller-handbook)
- [Etsy Community Forums](https://www.etsy.com/teams)

---

## Summary of Required Credentials

After completing this guide, you'll have:

1. **API Key** - From your Etsy app
2. **Shared Secret** - From your Etsy app
3. **Access Token** - Generated after authorizing
4. **Access Token Secret** - Generated after authorizing
5. **Shop ID** - From your shop settings

Add all five to your `.env` file to enable Etsy integration in AutoLister.
