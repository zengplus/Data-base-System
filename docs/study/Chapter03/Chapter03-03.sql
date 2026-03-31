-- 创建员工-主管关系表
CREATE TABLE emp_super (
    person TEXT NOT NULL,
    supervisor TEXT NOT NULL,
    PRIMARY KEY (person)
);

-- 插入测试数据
INSERT INTO emp_super (person, supervisor) VALUES
('Bob', 'Alice'),
('Mary', 'Susan'),
('Alice', 'David'),
('David', 'Mary');

-- 查询 Bob 的直接主管
SELECT supervisor AS bob_direct_supervisor
FROM emp_super
WHERE person = 'Bob';

-- 查询 Bob 的间接主管
SELECT e2.supervisor AS bob_super_supervisor
FROM emp_super e1
INNER JOIN emp_super e2 
  ON e1.supervisor = e2.person
WHERE e1.person = 'Bob';


-- 第一层：Bob → Alice
-- 第二层：Alice → David
-- 第三层：David → Mary
SELECT
  e1.supervisor AS level1_super,  -- 直接主管
  e2.supervisor AS level2_super,  -- 主管的主管
  e3.supervisor AS level3_super,   -- 主管的主管的主管
  e4.supervisor AS level4_super   -- 主管的主管的主管的主管
FROM emp_super e1
LEFT JOIN emp_super e2 ON e1.supervisor = e2.person
LEFT JOIN emp_super e3 ON e2.supervisor = e3.person
LEFT JOIN emp_super e4 ON e3.supervisor = e4.person
WHERE e1.person = 'Bob';



-- 查询 Bob 的所有主管（包括直接和间接）
WITH RECURSIVE supervisor_chain AS (
  SELECT 
    supervisor AS supervisor_name,
    1 AS hierarchy_level
  FROM emp_super
  WHERE person = 'Bob'

  UNION ALL

  -- 递归：向上找主管的主管
  SELECT 
    e.supervisor,
    sc.hierarchy_level + 1
  FROM supervisor_chain sc
  INNER JOIN emp_super e 
    ON sc.supervisor_name = e.person
)
SELECT supervisor_name, hierarchy_level
FROM supervisor_chain;