import base64
import boto3
import os
import json
from botocore.exceptions import ClientError

class KMSHelper:
    def __init__(self, region='us-east-1'):
        self.region = region
        self.kms_client = boto3.client('kms', region_name=region)
        self.key_id = os.getenv('KMS_KEY_ID', 'alias/library-db-credentials')
    
    def encrypt(self, plaintext):
        """تشفير نص باستخدام KMS"""
        try:
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            response = self.kms_client.encrypt(
                KeyId=self.key_id,
                Plaintext=plaintext
            )
            
            # تحويل إلى base64 للتخزين الآمن
            encrypted_blob = response['CiphertextBlob']
            return base64.b64encode(encrypted_blob).decode('utf-8')
            
        except ClientError as e:
            print(f"❌ Encryption error: {e}")
            return None
    
    def decrypt(self, encrypted_b64):
        """فك تشفير نص مشفر"""
        try:
            # تحويل من base64
            encrypted_blob = base64.b64decode(encrypted_b64)
            
            response = self.kms_client.decrypt(
                CiphertextBlob=encrypted_blob
            )
            
            return response['Plaintext'].decode('utf-8')
            
        except ClientError as e:
            print(f"❌ Decryption error: {e}")
            return None
    
    def encrypt_credentials(self, credentials_dict):
        """تشفير جميع credentials"""
        encrypted = {}
        for key, value in credentials_dict.items():
            if value:  # فقط إذا كانت القيمة موجودة
                encrypted[key] = self.encrypt(value)
        return encrypted
    
    def decrypt_credentials(self, encrypted_dict):
        """فك تشفير جميع credentials"""
        decrypted = {}
        for key, value in encrypted_dict.items():
            if value:  # فقط إذا كانت القيمة موجودة
                decrypted[key] = self.decrypt(value)
        return decrypted
    
    def save_encrypted_credentials(self, credentials_dict, filename='encrypted_credentials.json'):
        """حفظ credentials مشفرة إلى ملف"""
        encrypted = self.encrypt_credentials(credentials_dict)
        
        with open(filename, 'w') as f:
            json.dump(encrypted, f, indent=2)
        
        print(f"✅ Credentials encrypted and saved to {filename}")
        return encrypted
    
    def load_encrypted_credentials(self, filename='encrypted_credentials.json'):
        """تحميل وفك تشفير credentials من ملف"""
        try:
            with open(filename, 'r') as f:
                encrypted = json.load(f)
            
            decrypted = self.decrypt_credentials(encrypted)
            return decrypted
            
        except FileNotFoundError:
            print(f"❌ File {filename} not found")
            return None
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in {filename}")
            return None

# اختبار الوحدة
if __name__ == "__main__":
    kms = KMSHelper()
    
    print("🔐 Testing KMS Helper...")
    
    # تحميل وفك تشفير credentials
    credentials = kms.load_encrypted_credentials()
    
    if credentials:
        print("\n✅ Successfully decrypted credentials:")
        for key, value in credentials.items():
            if key == 'DB_PASSWORD':
                print(f"   {key}: {'*' * len(value)}")
            else:
                print(f"   {key}: {value}")
    else:
        print("\n❌ Failed to load credentials")
