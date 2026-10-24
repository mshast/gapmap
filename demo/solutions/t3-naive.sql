-- Deliberately incorrect: multiple refunds repeat the order amount.
SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region,
       SUM(o.amount_cents) - SUM(COALESCE(r.amount_cents, 0)) AS net_revenue_cents
FROM orders o
JOIN customers c ON c.id = o.customer_id
LEFT JOIN refunds r ON r.order_id = o.id
WHERE o.status = 'completed'
GROUP BY 1
ORDER BY 1;
