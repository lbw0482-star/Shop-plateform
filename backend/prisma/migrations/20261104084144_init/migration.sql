-- CreateTable
CREATE TABLE "member_level" (
    "level_id" SERIAL NOT NULL,
    "level_name" VARCHAR(30) NOT NULL,
    "min_points" INTEGER NOT NULL,
    "max_points" INTEGER,
    "sort_no" INTEGER NOT NULL DEFAULT 0,
    "status" CHAR(1) NOT NULL DEFAULT 'A',

    CONSTRAINT "member_level_pkey" PRIMARY KEY ("level_id")
);

-- CreateTable
CREATE TABLE "sys_user" (
    "user_id" SERIAL NOT NULL,
    "username" VARCHAR(50) NOT NULL,
    "password_hash" VARCHAR(255) NOT NULL,
    "must_change_password" BOOLEAN NOT NULL DEFAULT false,
    "gender" CHAR(1) NOT NULL DEFAULT 'U',
    "email" VARCHAR(100),
    "phone" VARCHAR(20),
    "register_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "total_points" INTEGER NOT NULL DEFAULT 0,
    "level_id" INTEGER NOT NULL,
    "account_status" CHAR(1) NOT NULL DEFAULT 'A',
    "last_login_time" TIMESTAMP(3),

    CONSTRAINT "sys_user_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "sys_admin" (
    "admin_id" SERIAL NOT NULL,
    "admin_name" VARCHAR(50) NOT NULL,
    "password_hash" VARCHAR(255) NOT NULL,
    "real_name" VARCHAR(50),
    "email" VARCHAR(100),
    "phone" VARCHAR(20),
    "status" CHAR(1) NOT NULL DEFAULT 'A',
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_login_time" TIMESTAMP(3),

    CONSTRAINT "sys_admin_pkey" PRIMARY KEY ("admin_id")
);

-- CreateTable
CREATE TABLE "sys_role" (
    "role_id" SERIAL NOT NULL,
    "role_code" VARCHAR(30) NOT NULL,
    "role_name" VARCHAR(50) NOT NULL,
    "description" VARCHAR(200),
    "status" CHAR(1) NOT NULL DEFAULT 'A',

    CONSTRAINT "sys_role_pkey" PRIMARY KEY ("role_id")
);

-- CreateTable
CREATE TABLE "sys_admin_role" (
    "admin_id" INTEGER NOT NULL,
    "role_id" INTEGER NOT NULL,

    CONSTRAINT "sys_admin_role_pkey" PRIMARY KEY ("admin_id","role_id")
);

-- CreateTable
CREATE TABLE "product_category" (
    "category_id" SERIAL NOT NULL,
    "category_name" VARCHAR(50) NOT NULL,
    "description" VARCHAR(200),
    "sort_no" INTEGER NOT NULL DEFAULT 0,
    "status" CHAR(1) NOT NULL DEFAULT 'A',
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "product_category_pkey" PRIMARY KEY ("category_id")
);

-- CreateTable
CREATE TABLE "product" (
    "product_id" SERIAL NOT NULL,
    "product_code" VARCHAR(30) NOT NULL,
    "product_name" VARCHAR(100) NOT NULL,
    "category_id" INTEGER NOT NULL,
    "stock_qty" INTEGER NOT NULL DEFAULT 0,
    "unit_price" DECIMAL(18,2) NOT NULL,
    "product_intro" TEXT,
    "recommend_flag" BOOLEAN NOT NULL DEFAULT false,
    "listing_date" TIMESTAMP(3),
    "product_points" INTEGER NOT NULL DEFAULT 0,
    "product_status" CHAR(1) NOT NULL DEFAULT 'D',
    "main_image_url" VARCHAR(255),
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_time" TIMESTAMP(3),

    CONSTRAINT "product_pkey" PRIMARY KEY ("product_id")
);

-- CreateTable
CREATE TABLE "product_image" (
    "image_id" SERIAL NOT NULL,
    "product_id" INTEGER NOT NULL,
    "image_url" VARCHAR(255) NOT NULL,
    "is_main" BOOLEAN NOT NULL DEFAULT false,
    "sort_no" INTEGER NOT NULL DEFAULT 0,
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "product_image_pkey" PRIMARY KEY ("image_id")
);

-- CreateTable
CREATE TABLE "cart" (
    "cart_id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_time" TIMESTAMP(3),

    CONSTRAINT "cart_pkey" PRIMARY KEY ("cart_id")
);

-- CreateTable
CREATE TABLE "cart_item" (
    "cart_item_id" SERIAL NOT NULL,
    "cart_id" INTEGER NOT NULL,
    "product_id" INTEGER NOT NULL,
    "quantity" INTEGER NOT NULL,
    "add_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_time" TIMESTAMP(3),

    CONSTRAINT "cart_item_pkey" PRIMARY KEY ("cart_item_id")
);

-- CreateTable
CREATE TABLE "member_address" (
    "address_id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "receiver_name" VARCHAR(50) NOT NULL,
    "receiver_phone" VARCHAR(20) NOT NULL,
    "address_detail" VARCHAR(255) NOT NULL,
    "is_default" BOOLEAN NOT NULL DEFAULT false,
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_time" TIMESTAMP(3),

    CONSTRAINT "member_address_pkey" PRIMARY KEY ("address_id")
);

-- CreateTable
CREATE TABLE "orders" (
    "order_id" SERIAL NOT NULL,
    "order_no" VARCHAR(32) NOT NULL,
    "user_id" INTEGER NOT NULL,
    "order_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "receiver_name" VARCHAR(50) NOT NULL,
    "receiver_phone" VARCHAR(20) NOT NULL,
    "receiver_address" VARCHAR(255) NOT NULL,
    "payment_method" VARCHAR(30) NOT NULL DEFAULT 'SIMULATED_ONLINE',
    "payment_status" CHAR(1) NOT NULL DEFAULT 'U',
    "order_status" CHAR(1) NOT NULL DEFAULT 'W',
    "total_amount" DECIMAL(18,2) NOT NULL,
    "earned_points" INTEGER NOT NULL DEFAULT 0,
    "remark" VARCHAR(500),
    "cancel_reason" VARCHAR(200),
    "refund_reason" VARCHAR(200),
    "refund_time" TIMESTAMP(3),
    "completed_time" TIMESTAMP(3),
    "updated_time" TIMESTAMP(3),

    CONSTRAINT "orders_pkey" PRIMARY KEY ("order_id")
);

-- CreateTable
CREATE TABLE "order_item" (
    "order_item_id" SERIAL NOT NULL,
    "order_id" INTEGER NOT NULL,
    "product_id" INTEGER NOT NULL,
    "product_name_snapshot" VARCHAR(100) NOT NULL,
    "unit_price" DECIMAL(18,2) NOT NULL,
    "quantity" INTEGER NOT NULL,
    "item_points" INTEGER NOT NULL DEFAULT 0,
    "subtotal" DECIMAL(18,2) NOT NULL,

    CONSTRAINT "order_item_pkey" PRIMARY KEY ("order_item_id")
);

-- CreateTable
CREATE TABLE "payment_record" (
    "payment_id" SERIAL NOT NULL,
    "order_id" INTEGER NOT NULL,
    "payment_no" VARCHAR(40) NOT NULL,
    "payment_method" VARCHAR(30) NOT NULL DEFAULT 'SIMULATED_ONLINE',
    "payment_amount" DECIMAL(18,2) NOT NULL,
    "payment_status" CHAR(1) NOT NULL DEFAULT 'U',
    "paid_time" TIMESTAMP(3),
    "transaction_reference" VARCHAR(64),
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "payment_record_pkey" PRIMARY KEY ("payment_id")
);

-- CreateTable
CREATE TABLE "member_message" (
    "message_id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "title" VARCHAR(100) NOT NULL,
    "content" TEXT NOT NULL,
    "message_status" CHAR(1) NOT NULL DEFAULT 'P',
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_time" TIMESTAMP(3),
    "reviewer_admin_id" INTEGER,
    "review_time" TIMESTAMP(3),

    CONSTRAINT "member_message_pkey" PRIMARY KEY ("message_id")
);

-- CreateTable
CREATE TABLE "message_reply" (
    "reply_id" SERIAL NOT NULL,
    "message_id" INTEGER NOT NULL,
    "admin_id" INTEGER NOT NULL,
    "content" TEXT NOT NULL,
    "created_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "message_reply_pkey" PRIMARY KEY ("reply_id")
);

-- CreateTable
CREATE TABLE "audit_log" (
    "log_id" SERIAL NOT NULL,
    "admin_id" INTEGER,
    "operation_type" VARCHAR(50) NOT NULL,
    "target_type" VARCHAR(50) NOT NULL,
    "target_id" VARCHAR(50),
    "operation_detail" VARCHAR(500),
    "operation_time" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ip_address" VARCHAR(45),

    CONSTRAINT "audit_log_pkey" PRIMARY KEY ("log_id")
);

-- CreateTable
CREATE TABLE "auth_session" (
    "session_id" VARCHAR(80) NOT NULL,
    "user_id" INTEGER,
    "admin_id" INTEGER,
    "expires_at" TIMESTAMP(3) NOT NULL,
    "revoked_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "auth_session_pkey" PRIMARY KEY ("session_id")
);

-- CreateTable
CREATE TABLE "point_transaction" (
    "transaction_id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "order_id" INTEGER,
    "points" INTEGER NOT NULL,
    "transaction_type" VARCHAR(30) NOT NULL,
    "idempotency_key" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "point_transaction_pkey" PRIMARY KEY ("transaction_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "member_level_level_name_key" ON "member_level"("level_name");

-- CreateIndex
CREATE UNIQUE INDEX "sys_user_username_key" ON "sys_user"("username");

-- CreateIndex
CREATE UNIQUE INDEX "sys_admin_admin_name_key" ON "sys_admin"("admin_name");

-- CreateIndex
CREATE UNIQUE INDEX "sys_role_role_code_key" ON "sys_role"("role_code");

-- CreateIndex
CREATE UNIQUE INDEX "product_category_category_name_key" ON "product_category"("category_name");

-- CreateIndex
CREATE UNIQUE INDEX "product_product_code_key" ON "product"("product_code");

-- CreateIndex
CREATE INDEX "product_product_status_category_id_idx" ON "product"("product_status", "category_id");

-- CreateIndex
CREATE UNIQUE INDEX "cart_user_id_key" ON "cart"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "cart_item_cart_id_product_id_key" ON "cart_item"("cart_id", "product_id");

-- CreateIndex
CREATE UNIQUE INDEX "orders_order_no_key" ON "orders"("order_no");

-- CreateIndex
CREATE INDEX "orders_user_id_order_status_order_time_idx" ON "orders"("user_id", "order_status", "order_time");

-- CreateIndex
CREATE UNIQUE INDEX "order_item_order_id_product_id_key" ON "order_item"("order_id", "product_id");

-- CreateIndex
CREATE UNIQUE INDEX "payment_record_payment_no_key" ON "payment_record"("payment_no");

-- CreateIndex
CREATE INDEX "audit_log_target_type_target_id_idx" ON "audit_log"("target_type", "target_id");

-- CreateIndex
CREATE INDEX "auth_session_expires_at_idx" ON "auth_session"("expires_at");

-- CreateIndex
CREATE UNIQUE INDEX "point_transaction_idempotency_key_key" ON "point_transaction"("idempotency_key");

-- CreateIndex
CREATE INDEX "point_transaction_user_id_created_at_idx" ON "point_transaction"("user_id", "created_at");

-- AddForeignKey
ALTER TABLE "sys_user" ADD CONSTRAINT "sys_user_level_id_fkey" FOREIGN KEY ("level_id") REFERENCES "member_level"("level_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sys_admin_role" ADD CONSTRAINT "sys_admin_role_admin_id_fkey" FOREIGN KEY ("admin_id") REFERENCES "sys_admin"("admin_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sys_admin_role" ADD CONSTRAINT "sys_admin_role_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "sys_role"("role_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "product" ADD CONSTRAINT "product_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "product_category"("category_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "product_image" ADD CONSTRAINT "product_image_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "product"("product_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "cart" ADD CONSTRAINT "cart_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "sys_user"("user_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "cart_item" ADD CONSTRAINT "cart_item_cart_id_fkey" FOREIGN KEY ("cart_id") REFERENCES "cart"("cart_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "cart_item" ADD CONSTRAINT "cart_item_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "product"("product_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "member_address" ADD CONSTRAINT "member_address_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "sys_user"("user_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "orders" ADD CONSTRAINT "orders_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "sys_user"("user_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "order_item" ADD CONSTRAINT "order_item_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "orders"("order_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "order_item" ADD CONSTRAINT "order_item_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "product"("product_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_record" ADD CONSTRAINT "payment_record_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "orders"("order_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "member_message" ADD CONSTRAINT "member_message_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "sys_user"("user_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "member_message" ADD CONSTRAINT "member_message_reviewer_admin_id_fkey" FOREIGN KEY ("reviewer_admin_id") REFERENCES "sys_admin"("admin_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "message_reply" ADD CONSTRAINT "message_reply_message_id_fkey" FOREIGN KEY ("message_id") REFERENCES "member_message"("message_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "message_reply" ADD CONSTRAINT "message_reply_admin_id_fkey" FOREIGN KEY ("admin_id") REFERENCES "sys_admin"("admin_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_log" ADD CONSTRAINT "audit_log_admin_id_fkey" FOREIGN KEY ("admin_id") REFERENCES "sys_admin"("admin_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "auth_session" ADD CONSTRAINT "auth_session_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "sys_user"("user_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "auth_session" ADD CONSTRAINT "auth_session_admin_id_fkey" FOREIGN KEY ("admin_id") REFERENCES "sys_admin"("admin_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "point_transaction" ADD CONSTRAINT "point_transaction_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "sys_user"("user_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "point_transaction" ADD CONSTRAINT "point_transaction_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "orders"("order_id") ON DELETE SET NULL ON UPDATE CASCADE;
