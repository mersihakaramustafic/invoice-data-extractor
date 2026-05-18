create table invoice_logs (
  id           uuid        primary key default gen_random_uuid(),
  document_id  uuid        references invoice_documents(id) on delete set null,
  file_name    text        not null,
  level        text        not null check (level in ('info', 'warning', 'error')),
  event        text        not null,
  message      text,
  created_at   timestamptz not null default now()
);
