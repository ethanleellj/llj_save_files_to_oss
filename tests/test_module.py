#!/usr/bin/env python3
import argparse
import xmlrpc.client

def test_module_install(host, database, user, password):
    common = xmlrpc.client.ServerProxy(f'http://localhost:8069/xmlrpc/2/common')
    uid = common.authenticate(database, user, password, {})
    
    if not uid:
        print("ERROR: Authentication failed")
        return False
    
    models = xmlrpc.client.ServerProxy(f'http://localhost:8069/xmlrpc/2/object')
    
    print("Testing llj_save_filestore_to_oss module...")
    try:
        models.execute_kw(database, uid, password, 'ir.module.module', 'search', [[('name', '=', 'llj_save_filestore_to_oss')]])
        print("✓ llj_save_filestore_to_oss module found")
    except Exception as e:
        print(f"✗ llj_save_filestore_to_oss module test failed: {e}")
        return False
    
    print("Testing llj_save_product_file_with_id_code module...")
    try:
        models.execute_kw(database, uid, password, 'ir.module.module', 'search', [[('name', '=', 'llj_save_product_file_with_id_code')]])
        print("✓ llj_save_product_file_with_id_code module found")
    except Exception as e:
        print(f"✗ llj_save_product_file_with_id_code module test failed: {e}")
        return False
    
    print("Testing llj_id_code field...")
    try:
        fields = models.execute_kw(database, uid, password, 'product.template', 'fields_get', [], {'attributes': ['string']})
        if 'llj_id_code' in fields:
            print("✓ llj_id_code field exists")
        else:
            print("✗ llj_id_code field not found")
            return False
    except Exception as e:
        print(f"✗ llj_id_code field test failed: {e}")
        return False
    
    print("\nAll tests passed!")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Odoo modules')
    parser.add_argument('--host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--user', default='admin', help='Odoo username')
    parser.add_argument('--password', default='admin', help='Odoo password')
    
    args = parser.parse_args()
    
    success = test_module_install(args.host, args.database, args.user, args.password)
    exit(0 if success else 1)