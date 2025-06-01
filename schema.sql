-- Disease diagnosis

CREATE TABLE diseases (
  id TEXT PRIMARY KEY,
  label TEXT,
  domain_id TEXT,
  description TEXT,
  included_in_diagnosis BOOLEAN,
  article_id TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  deleted_at TIMESTAMP,
  created_by TEXT,
  updated_by TEXT,
  deleted_by TEXT
);

CREATE TABLE domains (
  id TEXT PRIMARY KEY,
  domain TEXT,
  description TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  deleted_at TIMESTAMP,
  created_by TEXT,
  updated_by TEXT,
  deleted_by TEXT
);

CREATE TABLE disease_domain_crossmap (
  id TEXT PRIMARY KEY,
  disease_id_1 TEXT,
  domain_id_1 TEXT,
  disease_id_2 TEXT,
  domain_id_2 TEXT
);

CREATE TABLE diagnosis_log (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMP,
  image_content TEXT,
  text_content TEXT,
  result_text TEXT,
  result_reasoning TEXT
);

CREATE TABLE diagnosis_log_disease (
  id TEXT PRIMARY KEY,
  diagnosis_log_id TEXT,
  disease_id TEXT
);

-- Authentication

CREATE TABLE role (
  role_id TEXT PRIMARY KEY,
  role TEXT
);

CREATE TABLE user_token (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  token_hash TEXT,
  created_at TIMESTAMP,
  expired_at TIMESTAMP,
  revoked BOOLEAN,
  revoked_at TIMESTAMP
);

CREATE TABLE user_info (
  user_id TEXT PRIMARY KEY,
  username TEXT,
  hashpass TEXT,
  role_id TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  deleted_at TIMESTAMP
);

-- Article

CREATE TABLE articles (
  id TEXT PRIMARY KEY,
  title TEXT,
  summary TEXT,
  content TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  deleted_at TIMESTAMP,
  created_by TEXT,
  updated_by TEXT,
  deleted_by TEXT
);

CREATE TABLE clinics (
  id TEXT PRIMARY KEY,
  name TEXT,
  description TEXT,
  location TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  deleted_at TIMESTAMP,
  created_by TEXT,
  updated_by TEXT,
  deleted_by TEXT,
  phone_number TEXT,
  website TEXT
);

CREATE TABLE images (
    id TEXT PRIMARY KEY,
    base_url TEXT,
    rel_path TEXT,
    mime_type TEXT,
    uploaded_at TIMESTAMP,
    uploaded_by TEXT
);

CREATE TABLE image_usage (
    usage TEXT PRIMARY KEY,
    description TEXT
);

CREATE TABLE image_map (
    id TEXT PRIMARY KEY,
    image_id TEXT,
    object_type TEXT,   -- e.g., 'disease', 'clinic', 'article'
    object_id TEXT,
    usage TEXT -- e.g., 'thumbnail', 'cover'
);