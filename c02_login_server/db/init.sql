/* ============================================================
 * PostgreSQL 聊天系统数据库结构设计
 *
 * 模块说明：
 * 1. app_user        ：用户主体表（业务层）
 * 2. user_auth       ：用户登录与认证表（安全层）
 * 3. conversation    ：聊天会话表
 * 4. chat_message    ：聊天消息表
 *
 * 设计目标：
 * - 用户与登录方式解耦
 * - 支持多种登录方式（密码 / OAuth / 手机号）
 * - UUID 对外，BIGINT 对内
 * - 聊天记录可高效分页、裁剪、清理
 * ============================================================
 */


/* ============================================================
 * 一、启用必要扩展
 * ============================================================
 */

-- gen_random_uuid() 需要 pgcrypto 扩展
CREATE EXTENSION IF NOT EXISTS pgcrypto;


/* ============================================================
 * 二、用户主体表（app_user）
 * ============================================================
 *
 * 这是「业务用户」表：
 * - 不关心怎么登录
 * - 不存密码
 * - 用于绑定聊天、订单、会员等业务数据
 */

CREATE TABLE IF NOT EXISTS app_user (
  -- 内部主键：性能好，JOIN 快
  id BIGSERIAL PRIMARY KEY,

  -- 对外暴露的用户 ID（推荐前端 / API 使用）
  -- 避免暴露自增 ID，防止枚举攻击
  user_uuid UUID NOT NULL DEFAULT gen_random_uuid(),

  -- 昵称（可修改）
  nickname TEXT,

  -- 头像地址
  avatar_url TEXT,

  -- 用户状态
  -- 1  = 正常
  -- 0  = 禁用（可登录校验用）
  -- -1 = 软删除（历史数据保留）
  status SMALLINT NOT NULL DEFAULT 1,

  -- 创建时间
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),

  -- 更新时间（业务更新时手动维护）
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

  -- user_uuid 全局唯一
  CONSTRAINT uk_app_user_uuid UNIQUE (user_uuid)
);


/* ============================================================
 * 三、用户登录认证表（user_auth）
 * ============================================================
 *
 * 这是「安全层」表：
 * - 管理所有登录方式
 * - 一个用户可以有多种登录凭证
 * - 密码 / OAuth 完全通用
 */

CREATE TABLE IF NOT EXISTS user_auth (
  id BIGSERIAL PRIMARY KEY,

  -- 关联用户主体
  user_id BIGINT NOT NULL,

  -- 登录类型：
  -- password        用户名 + 密码
  -- email           邮箱登录
  -- phone           手机号登录
  -- oauth_github    GitHub OAuth
  -- oauth_wechat    微信 OAuth
  identity_type TEXT NOT NULL,

  -- 登录标识：
  -- 用户名 / 邮箱 / 手机号 / open_id
  identifier TEXT NOT NULL,

  -- 登录凭证：
  -- 密码登录：bcrypt / argon2 哈希
  -- OAuth：通常为空
  credential TEXT,

  -- 是否已验证（邮箱 / 手机）
  is_verified BOOLEAN NOT NULL DEFAULT FALSE,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

  -- 外键：删除用户时自动清理认证信息
  CONSTRAINT fk_user_auth_user
    FOREIGN KEY (user_id)
    REFERENCES app_user(id)
    ON DELETE CASCADE,

  -- 同一登录方式下 identifier 唯一
  CONSTRAINT uk_user_auth_identity UNIQUE (identity_type, identifier)
);


/* ============================================================
 * 四、聊天会话表（conversation）
 * ============================================================
 *
 * 一次「新的聊天窗口」就是一条会话
 */

CREATE TABLE IF NOT EXISTS conversation (
  id BIGSERIAL PRIMARY KEY,

  -- 归属用户（对外 UUID）
  user_id UUID NOT NULL,

  -- 会话标题（可由 AI 自动生成）
  title TEXT,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);


/* ============================================================
 * 五、聊天消息表（chat_message）
 * ============================================================
 *
 * 存储所有消息：
 * - user / assistant / system
 * - JSONB 支持多模态内容
 */

CREATE TABLE IF NOT EXISTS chat_message (
  id BIGSERIAL PRIMARY KEY,

  -- 关联会话
  conversation_id BIGINT NOT NULL,

  -- 消息角色：
  -- system / user / assistant / tool
  role TEXT NOT NULL,

  -- 消息内容（支持文本 / 结构化 / 多模态）
  content JSONB NOT NULL,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),

  -- 会话删除时，自动清理消息
  CONSTRAINT fk_chat_message_conversation
    FOREIGN KEY (conversation_id)
    REFERENCES conversation(id)
    ON DELETE CASCADE
);


/* ============================================================
 * 六、索引设计（非常关键）
 * ============================================================
 */

-- 登录查询（identity_type + identifier）
CREATE INDEX IF NOT EXISTS idx_user_auth_login
ON user_auth (identity_type, identifier);

-- 用户会话列表（最近会话）
CREATE INDEX IF NOT EXISTS idx_conversation_user_time
ON conversation (user_id, updated_at DESC);

-- 会话内最近 N 条消息（上下文裁剪用）
CREATE INDEX IF NOT EXISTS idx_chat_message_conversation_time
ON chat_message (conversation_id, created_at DESC);