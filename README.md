# Inventory and Order Management System

## Features
This system is designed for store owners to record material purchase, set product recipes, and manage both current and future orders. It automatically calculates product costs and revenue based on purchases and orders information. The system also supports modifying product pricing and recipes, applying different prices and material usage based on the time of modification and the time of order creation. This system consists of the following seven pages:
1. **Today's Orders**
2. **Future Orders**
3. **Previous Orders**
4. **Product Settings**
5. **Material Costs**
6. **Purchase Records**
7. **Supplier Information**

The interface is responsive and can be viewed on different display setups. The following sections show the features of each page using the mobile screen size (390x844).
![responsive](https://github.com/user-attachments/assets/bd63f0f1-4ff0-4079-815d-072d75d77a4c)


### 1. Today's Orders
Allows the creation of sales orders for the day based on the set products. After creating an order, the order status (completed, canceled, in preparation) can be marked, and orders can also be modified or deleted.  
*Note: Completed orders are hidden by default.*
![order](https://github.com/user-attachments/assets/8fa2cb4d-3914-40f3-b5ac-b16972ee7502)


### 2. Future Orders
Includes all the features of Today's Orders, with additional fields for order completion date, remaining time reminders, and payment status.
![future_order](https://github.com/user-attachments/assets/dd19d68c-d482-4cb3-9df6-2753ea111afb)

### 3. Previous Orders
Displays a summary of previous daily orders (quantity, total cost, total revenue). Clicking on a date reveals all orders for that day, and the status (payment, completion) or contents of the orders can be modified.  
*Note: The status bar for past orders is hidden by default to prevent accidental clicks; it can be displayed by pressing a button.*
![previous_order](https://github.com/user-attachments/assets/13cbed35-549d-4b0a-ae1f-7ba3de165ac2)

### 4. Product Settings
Records and displays product recipes and pricing. The system automatically calculates product costs based on recipe contents. If the product price or recipe is modified, the changes will be applied to different orders according to the modification time and order creation time.
![recipe](https://github.com/user-attachments/assets/b1b7fe19-6888-4fec-b3ec-e308b555ce3b)

### 5. Material Costs
Calculates and displays the total stock and cost per gram of materials, based on the quantities and prices recorded in the purchase records, as well as the usage and cost of materials in completed orders.
![materials](https://github.com/user-attachments/assets/26a8de2f-faf8-448b-829f-b21da516b19d)

### 6. Purchase Records
Records and displays details of material purchase records from suppliers.
![purchase](https://github.com/user-attachments/assets/72766d55-cae3-49f3-8316-447daa8e32e7)

### 7. Supplier Information
Records and displays details of supplier information. Only fields with data will be shown.
![vendor](https://github.com/user-attachments/assets/53964da7-4f8a-4845-9de6-8dbc4e128eff)
