-- 会话表
CREATE TABLE IF NOT EXISTS conversation (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 聊天记录表
CREATE TABLE IF NOT EXISTS chat_message (
  id BIGSERIAL PRIMARY KEY,
  conversation_id BIGINT NOT NULL,
  role TEXT NOT NULL,
  content JSONB NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),

  CONSTRAINT fk_conversation
    FOREIGN KEY (conversation_id)
    REFERENCES conversation(id)
    ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX idx_chat_message_conversation_time
ON chat_message (conversation_id, created_at DESC);

