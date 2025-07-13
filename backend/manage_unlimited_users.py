#!/usr/bin/env python3
"""
Script to manage unlimited users whitelist.
This allows you to add/remove users from the unlimited access list.
"""

import sys
import os
from typing import Set

def get_unlimited_users_from_file() -> Set[str]:
    """Read current unlimited users from billing.py file."""
    billing_file = "services/billing.py"
    
    if not os.path.exists(billing_file):
        print(f"Error: {billing_file} not found")
        return set()
    
    with open(billing_file, 'r') as f:
        content = f.read()
    
    # Extract emails from UNLIMITED_USERS set
    start = content.find('UNLIMITED_USERS = {')
    if start == -1:
        print("Error: UNLIMITED_USERS not found in billing.py")
        return set()
    
    end = content.find('}', start)
    if end == -1:
        print("Error: Could not parse UNLIMITED_USERS")
        return set()
    
    # Extract the content between braces
    users_content = content[start:end+1]
    
    # Parse emails (simple extraction)
    emails = set()
    for line in users_content.split('\n'):
        line = line.strip()
        if '"' in line and '@' in line:
            # Extract email from quotes
            start_quote = line.find('"')
            end_quote = line.find('"', start_quote + 1)
            if start_quote != -1 and end_quote != -1:
                email = line[start_quote + 1:end_quote]
                if '@' in email:
                    emails.add(email)
    
    return emails

def update_unlimited_users_in_file(users: Set[str]) -> bool:
    """Update the UNLIMITED_USERS set in billing.py file."""
    billing_file = "services/billing.py"
    
    if not os.path.exists(billing_file):
        print(f"Error: {billing_file} not found")
        return False
    
    with open(billing_file, 'r') as f:
        content = f.read()
    
    # Find UNLIMITED_USERS definition
    start = content.find('UNLIMITED_USERS = {')
    if start == -1:
        print("Error: UNLIMITED_USERS not found in billing.py")
        return False
    
    end = content.find('}', start)
    if end == -1:
        print("Error: Could not parse UNLIMITED_USERS")
        return False
    
    # Create new users set string
    if users:
        users_str = 'UNLIMITED_USERS = {\n'
        for user in sorted(users):
            users_str += f'    "{user}",\n'
        users_str += '}'
    else:
        users_str = 'UNLIMITED_USERS = set()'
    
    # Replace in content
    new_content = content[:start] + users_str + content[end+1:]
    
    # Write back to file
    with open(billing_file, 'w') as f:
        f.write(new_content)
    
    return True

def list_users():
    """List all unlimited users."""
    users = get_unlimited_users_from_file()
    if users:
        print("Current unlimited users:")
        for user in sorted(users):
            print(f"  - {user}")
        print(f"\nTotal: {len(users)} users")
    else:
        print("No unlimited users configured.")

def add_user(email: str):
    """Add a user to the unlimited list."""
    if '@' not in email:
        print(f"Error: '{email}' doesn't look like a valid email address")
        return False
    
    users = get_unlimited_users_from_file()
    if email in users:
        print(f"User '{email}' is already in the unlimited list")
        return True
    
    users.add(email)
    if update_unlimited_users_in_file(users):
        print(f"Added '{email}' to unlimited users list")
        return True
    else:
        print(f"Failed to add '{email}' to unlimited users list")
        return False

def remove_user(email: str):
    """Remove a user from the unlimited list."""
    users = get_unlimited_users_from_file()
    if email not in users:
        print(f"User '{email}' is not in the unlimited list")
        return True
    
    users.remove(email)
    if update_unlimited_users_in_file(users):
        print(f"Removed '{email}' from unlimited users list")
        return True
    else:
        print(f"Failed to remove '{email}' from unlimited users list")
        return False

def show_help():
    """Show help message."""
    print("""
Unlimited Users Management Script

Usage:
    python manage_unlimited_users.py <command> [arguments]

Commands:
    list                    - List all unlimited users
    add <email>            - Add user to unlimited list
    remove <email>         - Remove user from unlimited list
    help                   - Show this help message

Examples:
    python manage_unlimited_users.py list
    python manage_unlimited_users.py add user@example.com
    python manage_unlimited_users.py remove user@example.com
""")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_users()
    elif command == 'add':
        if len(sys.argv) < 3:
            print("Error: Please provide an email address")
            return
        add_user(sys.argv[2])
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("Error: Please provide an email address")
            return
        remove_user(sys.argv[2])
    elif command == 'help':
        show_help()
    else:
        print(f"Error: Unknown command '{command}'")
        show_help()

if __name__ == "__main__":
    main() 