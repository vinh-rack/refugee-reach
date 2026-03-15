-- Seed a test user with WhatsApp preference enabled.
-- Safe to run repeatedly.

WITH upsert_user AS (
    INSERT INTO users (
        id,
        external_id,
        email,
        full_name,
        is_active
    )
    VALUES (
        '1d7f5cf9-2b57-4f48-8e2a-4f6d2c58d221',
        'whatsapp-test-user',
        'whatsapp.test.user@example.com',
        'WhatsApp Test User',
        TRUE
    )
    ON CONFLICT (external_id)
    DO UPDATE SET
        email = EXCLUDED.email,
        full_name = EXCLUDED.full_name,
        is_active = EXCLUDED.is_active
    RETURNING id
)
INSERT INTO user_preferences (
    user_id,
    min_severity,
    topics,
    regions,
    telegram_enabled,
    telegram_chat_id,
    whatsapp_enabled,
    whatsapp_phone,
    messenger_enabled,
    messenger_psid,
    created_at,
    updated_at
)
SELECT
    id,
    0.8,
    NULL,
    NULL,
    FALSE,
    NULL,
    TRUE,
    '84937108135',
    FALSE,
    NULL,
    now(),
    now()
FROM upsert_user
ON CONFLICT (user_id)
DO UPDATE SET
    min_severity = EXCLUDED.min_severity,
    topics = EXCLUDED.topics,
    regions = EXCLUDED.regions,
    telegram_enabled = EXCLUDED.telegram_enabled,
    telegram_chat_id = EXCLUDED.telegram_chat_id,
    whatsapp_enabled = EXCLUDED.whatsapp_enabled,
    whatsapp_phone = EXCLUDED.whatsapp_phone,
    messenger_enabled = EXCLUDED.messenger_enabled,
    messenger_psid = EXCLUDED.messenger_psid,
    updated_at = now();
