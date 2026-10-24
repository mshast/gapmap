SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region,
       SUM(o.amount_cents) AS gross_revenue_cents
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
GROUP BY 1
ORDER BY 1;
