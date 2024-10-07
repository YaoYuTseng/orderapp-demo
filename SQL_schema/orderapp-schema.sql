CREATE SCHEMA `orderapp`;

CREATE TABLE `orderapp`.`users` (
`user_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
`user_name` VARCHAR(100) NOT NULL,
`hashed_password` VARCHAR(100) NOT NULL);

CREATE TABLE `orderapp`.`products` (
`product_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
`product_name` VARCHAR(100) NOT NULL,
`uom_id` INT NOT NULL,
UNIQUE INDEX `product_name_UNIQUE` (`product_name` ASC) VISIBLE);

CREATE TABLE `orderapp`.`product_prices` (
`product_id` INT NOT NULL,
`price` INT NOT NULL,
`effective_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
PRIMARY KEY (`product_id`, `effective_timestamp`)
);

CREATE TABLE `orderapp`.`uom` (
`uom_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
`uom_name` VARCHAR(10) NOT NULL,
UNIQUE INDEX `uom_name_UNIQUE` (`uom_name` ASC) VISIBLE);

ALTER TABLE `orderapp`.`product_prices` 
ADD INDEX `fk_prices_products_idx` (`product_id` ASC) VISIBLE;
ALTER TABLE `orderapp`.`product_prices` 
ADD CONSTRAINT `fk_prices_products`
  FOREIGN KEY (`product_id`)
  REFERENCES `orderapp`.`products` (`product_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT;

ALTER TABLE `orderapp`.`products` 
ADD INDEX `fk_products_uom_idx` (`uom_id` ASC) VISIBLE;
ALTER TABLE `orderapp`.`products` 
ADD CONSTRAINT `fk_products_uom`
  FOREIGN KEY (`uom_id`)
  REFERENCES `orderapp`.`uom` (`uom_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT;
  
CREATE TABLE `orderapp`.`materials`(
`material_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
`material_name` VARCHAR(100) NOT NULL,
`uom_id` INT NOT NULL DEFAULT 3,
UNIQUE INDEX `material_name_UNIQUE` (`material_name` ASC) VISIBLE);

ALTER TABLE `orderapp`.`materials` 
ADD INDEX `fk_materials_uom_idx` (`uom_id` ASC) VISIBLE;
ALTER TABLE `orderapp`.`materials` 
ADD CONSTRAINT `fk_materials_uom`
  FOREIGN KEY (`uom_id`)
  REFERENCES `orderapp`.`uom` (`uom_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT;
  
CREATE TABLE `orderapp`.`orders` (
`order_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
`customer_id` INT NOT NULL DEFAULT 1,
`price_total` INT NOT NULL,
`order_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
`completion_timestamp` TIMESTAMP,
`order_status` ENUM("準備中", "已完成", "已取消") DEFAULT "準備中",
`is_paid` BOOLEAN DEFAULT TRUE,
`note` VARCHAR(255));

CREATE TABLE `orderapp`.`customers` (
`customer_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
`customer_family_name` VARCHAR(50),
`customer_given_name` VARCHAR(50),
`sex` VARCHAR(5),
`mobile_phone` VARCHAR(20),
UNIQUE INDEX `customer_given_name_UNIQUE` (`customer_given_name` ASC) VISIBLE);

ALTER TABLE `orderapp`.`orders` 
ADD INDEX `fk_orders_customers_idx` (`customer_id` ASC) VISIBLE;
ALTER TABLE `orderapp`.`orders` 
ADD CONSTRAINT `fk_orders_customers`
  FOREIGN KEY (`customer_id`)
  REFERENCES `orderapp`.`customers` (`customer_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT;

CREATE TABLE `orderapp`.`recipes`(
`product_id` INT NOT NULL,
`material_id` INT NOT NULL,
`quantity` DECIMAL(10, 2) NOT NULL,
`start_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
`end_timestamp` TIMESTAMP,
PRIMARY KEY (`product_id`, `material_id`, `start_timestamp`));

CREATE TABLE `orderapp`.`order_details`(
`order_id` INT NOT NULL,
`product_id` INT NOT NULL,
`quantity` DECIMAL(10, 2) NOT NULL,
PRIMARY KEY (`order_id`, `product_id`));

ALTER TABLE `orderapp`.`recipes` 
ADD INDEX `fk_recipes_materials_idx` (`material_id` ASC) VISIBLE;
ALTER TABLE `orderapp`.`recipes` 
ADD CONSTRAINT `fk_recipes_products`
  FOREIGN KEY (`product_id`)
  REFERENCES `orderapp`.`products` (`product_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT,
ADD CONSTRAINT `fk_recipes_materials`
  FOREIGN KEY (`material_id`)
  REFERENCES `orderapp`.`materials` (`material_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT;

ALTER TABLE `orderapp`.`order_details` 
ADD INDEX `fk_odetails_products_idx` (`product_id` ASC) VISIBLE;
ALTER TABLE `orderapp`.`order_details` 
ADD CONSTRAINT `fk_odetails_orders`
  FOREIGN KEY (`order_id`)
  REFERENCES `orderapp`.`orders` (`order_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT,
ADD CONSTRAINT `fk_odetails_products`
  FOREIGN KEY (`product_id`)
  REFERENCES `orderapp`.`products` (`product_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT;

CREATE TABLE `orderapp`.`purchases`(
`purchase_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
`vendor_id` INT NOT NULL,
`purchase_date` DATE NOT NULL,
`record_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE `orderapp`.`vendors`(
    `vendor_id` INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    `vendor_name` VARCHAR(255) NOT NULL,
    `office_phone` VARCHAR(20),
    `mobile_phone` VARCHAR(20),
    `address` VARCHAR(255),
    `tax_id` VARCHAR(20),
    `contact_name` VARCHAR(100),
    `contact_mobile_phone` VARCHAR(20),
    `open_days` SET('星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'),
    `note` VARCHAR(255)
);

CREATE TABLE `orderapp`.`purchase_details`(
`purchase_id` INT NOT NULL,
`material_id` INT NOT NULL,
`quantity` DECIMAL(10, 2) NOT NULL,
`price_total` INT NOT NULL,
PRIMARY KEY (`purchase_id`, `material_id`));

ALTER TABLE `orderapp`.`purchases`
ADD INDEX `fk_purchases_vendors_idx` (`vendor_id` ASC) VISIBLE;
ALTER TABLE `orderapp`.`purchases`
ADD CONSTRAINT `fk_purchases_vendors`
	FOREIGN KEY (`vendor_id`)
    REFERENCES `orderapp`.`vendors` (`vendor_id`)
    ON DELETE NO ACTION
    ON UPDATE RESTRICT;

ALTER TABLE `orderapp`.`purchase_details` 
ADD INDEX `fk_pdetails_materials_idx` (`material_id` ASC) VISIBLE;
ALTER TABLE `orderapp`.`purchase_details` 
ADD CONSTRAINT `fk_pdetails_purchases`
  FOREIGN KEY (`purchase_id`)
  REFERENCES `orderapp`.`purchases` (`purchase_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT,
ADD CONSTRAINT `fk_pdetails_materials`
  FOREIGN KEY (`material_id`)
  REFERENCES `orderapp`.`materials` (`material_id`)
  ON DELETE NO ACTION
  ON UPDATE RESTRICT;

CREATE TABLE `orderapp`.`material_costs` (
  `material_id` INT NOT NULL,
  `cost_date` DATE NOT NULL,
  `stocked_quantity` DECIMAL(10, 2) NOT NULL,
  `stocked_cost` DECIMAL(10, 2) NOT NULL,
  `cost_per_unit` DECIMAL(10, 5) NOT NULL,
  `record_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`material_id`, `cost_date`),
  INDEX `idx_material_costs_date` (`cost_date`),
  CONSTRAINT `fk_material_costs_materials`
    FOREIGN KEY (`material_id`)
    REFERENCES `orderapp`.`materials` (`material_id`)
    ON DELETE NO ACTION
    ON UPDATE RESTRICT
);

CREATE TABLE `orderapp`.`product_costs` (
  `product_id` INT NOT NULL,
  `cost_date` DATE NOT NULL,
  `cost_per_unit` DECIMAL(10, 5) NOT NULL,
  `record_timestamp` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`product_id`, `cost_date`),
  INDEX `idx_product_costs_date` (`cost_date`),
  CONSTRAINT `fk_product_costs_products`
    FOREIGN KEY (`product_id`)
    REFERENCES `orderapp`.`products` (`product_id`)
    ON DELETE NO ACTION
    ON UPDATE RESTRICT
);
INSERT INTO `orderapp`.`uom` (uom_name) VALUES ("未定義");
INSERT INTO `orderapp`.`uom` (uom_name) VALUES ("克");
INSERT INTO `orderapp`.`uom` (uom_name) VALUES ("顆");
INSERT INTO `orderapp`.`uom` (uom_name) VALUES ("個");
INSERT INTO `orderapp`.`vendors` (vendor_name) VALUES ("無資料");
INSERT INTO `orderapp`.`customers` (customer_given_name) VALUES ("無資料");
INSERT INTO `orderapp`.`users` (user_name, hashed_password) VALUES ("root","$2b$12$a/IJh6YgpHp/.nAdOJ9iGuFONrz2fpbvIQHRUDZ7Kp.06JUy9i3DG");
INSERT INTO `orderapp`.`users` (user_name, hashed_password) VALUES ("ireven2001","$2b$12$6wVb.LleTpgmRav4BsLa7OsOI2J.vaKJJ14PQzvqb35sVJJ4yVY5G")