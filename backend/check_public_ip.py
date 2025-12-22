import socket

hostname = "library-project-db.cuuhnwdvvtih.us-east-1.rds.amazonaws.com"

try:
    # جرب مع عدة DNS servers
    dns_servers = ['8.8.8.8', '1.1.1.1', '208.67.222.222']
    
    for dns in dns_servers:
        print(f"\nChecking with DNS: {dns}")
        
        import subprocess
        cmd = ['nslookup', hostname, dns]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if 'Address' in result.stdout:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Address:' in line and not '#53' in line:
                    ip = line.split(':')[1].strip()
                    print(f"IP: {ip}")
                    
                    # تحليل نوع IP
                    if ip.startswith('172.31.'):
                        print("⚠️  PRIVATE IP - RDS is NOT publicly accessible")
                        print("   Go to RDS → Modify → Public accessibility → Yes")
                    elif ip.startswith('54.') or ip.startswith('52.') or ip.startswith('34.'):
                        print("✅ PUBLIC IP - RDS is publicly accessible")
                    else:
                        print(f"ℹ️  Unknown IP type: {ip}")
        
except Exception as e:
    print(f"Error: {e}")
