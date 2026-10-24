SELECT o.id AS order_id,
       COALESCE(NULLIF(c.region, ''), 'Unknown') AS region,
       o.amount_cents
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
ORDER BY o.id;
