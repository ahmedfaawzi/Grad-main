import boto3
import base64
import json

def create_kms_key_and_encrypt():
    print("🔐 Creating KMS Key and encrypting credentials...")
    
    # تهيئة KMS client
    kms = boto3.client('kms', region_name='us-east-1')
    
    # 1. إنشاء KMS Key
    try:
        response = kms.create_key(
            Description='Library Database Credentials',
            KeyUsage='ENCRYPT_DECRYPT',
            Origin='AWS_KMS'
        )
        
        key_id = response['KeyMetadata']['KeyId']
        print(f"✅ KMS Key created: {key_id}")
        
        # 2. إنشاء Alias
        kms.create_alias(
            AliasName='alias/library-db-credentials',
            TargetKeyId=key_id
        )
        print("✅ Alias created: alias/library-db-credentials")
        
    except kms.exceptions.AlreadyExistsException:
        print("ℹ️  KMS Key already exists, using existing key...")
        key_id = 'alias/library-db-credentials'
    
    # 3. تشفير credentials
    credentials = {
        'DB_HOST': 'localhost',
        'DB_USER': 'admin',
        'DB_PASSWORD': 'ahmed1911',
        'DB_NAME': 'library_db',
        'DB_PORT': '3306'
    }
    
    encrypted_credentials = {}
    
    for key, value in credentials.items():
        try:
            # تشفير القيمة
            response = kms.encrypt(
                KeyId=key_id,
                Plaintext=value.encode('utf-8')
            )
            
            # تحويل إلى base64 للتخزين
            encrypted_blob = response['CiphertextBlob']
            encrypted_b64 = base64.b64encode(encrypted_blob).decode('utf-8')
            
            encrypted_credentials[key] = encrypted_b64
            print(f"✅ Encrypted {key}")
            
        except Exception as e:
            print(f"❌ Failed to encrypt {key}: {e}")
    
    # 4. حفظ المشفرات إلى ملف
    with open('encrypted_credentials.json', 'w') as f:
        json.dump(encrypted_credentials, f, indent=2)
    
    print(f"\n✅ Encrypted credentials saved to encrypted_credentials.json")
    
    # 5. اختبار فك التشفير
    print("\n🔍 Testing decryption...")
    test_decryption(encrypted_credentials, key_id)

def test_decryption(encrypted_credentials, key_id):
    kms = boto3.client('kms', region_name='us-east-1')
    
    for key, encrypted_b64 in encrypted_credentials.items():
        try:
            encrypted_blob = base64.b64decode(encrypted_b64)
            
            response = kms.decrypt(CiphertextBlob=encrypted_blob)
            decrypted = response['Plaintext'].decode('utf-8')
            
            if key == 'DB_PASSWORD':
                print(f"   {key}: {'*' * len(decrypted)} (decrypted successfully)")
            else:
                print(f"   {key}: {decrypted} (decrypted successfully)")
                
        except Exception as e:
            print(f"❌ Failed to decrypt {key}: {e}")

if __name__ == "__main__":
    create_kms_key_and_encrypt()
