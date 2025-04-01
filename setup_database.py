#!/usr/bin/env python3
"""
Database Setup Script for Email Support System
This script creates the database and tables needed for the email support system.
"""
import os
import mysql.connector
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Get database credentials from environment variables
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "email_support")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "email_support_pass")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "email_support_system")

def setup_database():
    """Set up the database using the schema file"""
    # Read the schema file
    try:
        with open("emailsys.sql", "r") as file:
            schema = file.read()
    except FileNotFoundError:
        print("Error: emailsys.sql schema file not found.")
        return False
    
    # Connect to MySQL server without specifying a database
    try:
        print(f"Connecting to MySQL server at {MYSQL_HOST}...")
        # First connect without specifying a database to create it if it doesn't exist
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        
        print("Connected to MySQL server.")
        cursor = connection.cursor()
        
        # Execute the schema file
        print("Creating database and tables...")
        
        # Split the schema into separate statements
        statements = schema.split(';')
        
        for statement in statements:
            # Skip empty statements
            if statement.strip():
                cursor.execute(statement)
                
        connection.commit()
        print(f"Database '{MYSQL_DATABASE}' created successfully.")
        
        # Close the connection
        cursor.close()
        connection.close()
        
        # Test connection to the new database
        test_connection()
        
        return True
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

def test_connection():
    """Test the connection to the database"""
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"Successfully connected to database '{MYSQL_DATABASE}'")
        print("Tables found:")
        for table in tables:
            print(f"- {table[0]}")
            
        cursor.close()
        connection.close()
        
        return True
    except Exception as e:
        print(f"Error testing database connection: {e}")
        return False

if __name__ == "__main__":
    print("Email Support System - Database Setup")
    print("=====================================")
    
    if setup_database():
        print("\nDatabase setup completed successfully!")
        sys.exit(0)
    else:
        print("\nDatabase setup failed. Please check the error messages above.")
        sys.exit(1) 