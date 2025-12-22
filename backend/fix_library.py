#!/usr/bin/env python3
import re

print("Fixing indentation in library_mysql.py...")

# قراءة الملف
with open('library_mysql.py', 'r') as f:
    content = f.read()

# إصلاح المسافات - تأكد من أن كل سطر يبدأ بمسافات صحيحة
lines = content.split('\n')
fixed_lines = []

for line in lines:
    # إزالة مسافات زائدة
    line = line.rstrip()
    
    # إذا كان السطر يحتوي على temp_config.pop
    if 'temp_config.pop' in line:
        line = '            ' + line.lstrip()
    
    fixed_lines.append(line)

# كتابة الملف المعدل
with open('library_mysql.py', 'w') as f:
    f.write('\n'.join(fixed_lines))

print("✅ File fixed!")
