/* ======================== 基础数据操作（DML/DDL） ======================== */
-- 时间点：21:31
-- 查询未教课教员信息
SELECT name 
FROM instructor 
WHERE ID NOT IN (SELECT ID FROM teaches);

-- 时间点：23:59
-- 1. 插入单条教员数据
INSERT INTO instructor 
VALUES ('1021', 'Smth', 'Biology', 66);

-- 2. 删除student表中所有元组（保留表结构）
DELETE FROM student;

-- 3. 永久删除表r（表结构+数据全部删除）
DROP TABLE r;

-- 4. 为表r添加属性A（数据类型D，现有记录该字段为NULL）
ALTER TABLE r 
ADD A D;

-- 5. 删除表r中的属性A（多数数据库需COLUMN关键字，部分数据库不支持）
ALTER TABLE r 
DROP COLUMN A;

/* ======================== 基础查询语法 ======================== */
-- 时间点：25:30
-- 1. 基本查询结构模板（A=属性，r=表，P=条件）
SELECT A1, A2, ..., An 
FROM r1, r2, ..., rm 
WHERE P;

-- 2. 算术运算查询（计算月薪）
SELECT ID, 
       name, 
       salary/12  -- 年薪/12得到月薪
FROM instructor;

-- 3. 算术运算结果重命名（给计算列起别名）
SELECT ID, 
       name, 
       salary/12 AS monthly_salary  -- 别名monthly_salary
FROM instructor;

-- 4. 表重命名与自连接查询（查询工资高于任意计算机系教员的教员）
SELECT DISTINCT T.name 
FROM instructor AS T,  -- 表别名T
     instructor AS S   -- 表别名S
WHERE T.salary > S.salary 
  AND S.dept_name = 'Comp.Sci.';

-- 时间点：26:49
-- 1. 字符串模糊查询（姓名包含"dar"子串）
SELECT name 
FROM instructor 
WHERE name LIKE '%dar%';  -- %匹配任意字符

-- 2. 匹配含百分号的字符串（转义字符\）
SELECT name 
FROM instructor 
WHERE name LIKE '100\%' ESCAPE '\';  -- 匹配"100%"

-- 3. 按姓名升序排序（默认ASC可省略）
SELECT DISTINCT name 
FROM instructor 
ORDER BY name;

-- 4. 按姓名降序排序
SELECT DISTINCT name 
FROM instructor 
ORDER BY name DESC;

-- 5. 多属性排序（先按系名升序，再按姓名升序）
SELECT DISTINCT name 
FROM instructor 
ORDER BY dept_name, name;

-- 时间点：32:11
-- 1. 工资区间查询（90000 ≤ salary ≤ 100000）
SELECT *  -- 查询所有列
FROM instructor 
WHERE salary BETWEEN 90000 AND 100000;

-- 2. 多属性元组比较查询（匹配ID和指定系名）
SELECT * 
FROM instructor, teaches 
WHERE (instructor.ID, instructor.dept_name) = (teaches.ID, 'Biology');

/* ======================== 集合运算 ======================== */
-- 时间点：34:07
-- 1. 集合并操作（去重）：2017秋季 或 2018春季开课的课程
(SELECT course_id 
 FROM section 
 WHERE sem = 'Fall' AND year=2017) 
UNION 
(SELECT course_id 
 FROM section 
 WHERE sem='Spring' AND year=2018);

-- 2. 集合并操作（保留重复）
(SELECT course_id 
 FROM section 
 WHERE sem = 'Fall' AND year=2017) 
UNION ALL 
(SELECT course_id 
 FROM section 
 WHERE sem='Spring' AND year=2018);

-- 3. 集合交操作（去重）：2017秋季 且 2018春季都开课的课程
(SELECT course_id 
 FROM section 
 WHERE sem = 'Fall' AND year= 2017) 
INTERSECT 
(SELECT course_id 
 FROM section 
 WHERE sem ='Spring' AND year =2018);

-- 4. 集合交操作（保留重复）
(SELECT course_id 
 FROM section 
 WHERE sem = 'Fall' AND year= 2017) 
INTERSECT ALL 
(SELECT course_id 
 FROM section 
 WHERE sem ='Spring' AND year =2018);

-- 5. 集合差操作（去重）：2017秋季开课 但 2018春季不开课的课程
(SELECT course_id 
 FROM section 
 WHERE sem = 'Fall' AND year= 2017) 
EXCEPT 
(SELECT course_id 
 FROM section 
 WHERE sem ='Spring' AND year =2018);

-- 6. 集合差操作（保留重复）
(SELECT course_id 
 FROM section 
 WHERE sem = 'Fall' AND year= 2017) 
EXCEPT ALL 
(SELECT course_id 
 FROM section 
 WHERE sem ='Spring' AND year =2018);

/* ======================== 空值与聚合函数 ======================== */
-- 时间点：36:39
-- 1. 查询工资为空的教员
SELECT name 
FROM instructor 
WHERE salary IS NULL;

-- 2. 查询工资不为空的教员
SELECT name 
FROM instructor 
WHERE salary IS NOT NULL;

-- 时间点：38:34
-- 1. 聚合函数：计算计算机系教员平均工资
SELECT AVG(salary) AS avg_salary
FROM instructor 
WHERE dept_name= 'Comp.Sci.';

-- 2. 聚合函数：统计2018春季授课的不同教员数（去重）
SELECT COUNT(DISTINCT ID) AS instructor_count
FROM teaches 
WHERE semester = 'Spring' AND year =2018;

-- 3. 聚合函数：统计课程表总记录数（不忽略NULL）
SELECT COUNT(*) AS total_courses
FROM course;

-- 4. 分组聚合：按系统计平均工资
SELECT dept_name, 
       AVG(salary) AS avg_salary 
FROM instructor 
GROUP BY dept_name;

-- 分组聚合错误示例（非聚合字段ID未在GROUP BY中，标准SQL报错）
-- SELECT dept_name,ID,avg (salary) from instructor group by dept_name;

-- 5. 分组后筛选：只显示平均工资>42000的系
SELECT dept_name, 
       AVG(salary) AS avg_salary 
FROM instructor 
GROUP BY dept_name 
HAVING AVG(salary)>42000;

/* ======================== 子查询 ======================== */
-- 时间点：01:00:59
-- 1. IN子查询：2017秋季开课 且 2018春季也开课的课程
SELECT DISTINCT course_id 
FROM section 
WHERE semester = 'Fall' AND year= 2017 
  AND course_id IN (SELECT course_id 
                    FROM section 
                    WHERE semester = 'Spring' AND year= 2018);

-- 2. NOT IN子查询：2017秋季开课 但 2018春季不开课的课程
SELECT DISTINCT course_id 
FROM section 
WHERE semester = 'Fall' AND year= 2017 
  AND course_id NOT IN (SELECT course_id 
                        FROM section 
                        WHERE semester = 'Spring' AND year= 2018);

-- 3. 固定值NOT IN：查询姓名不是Mozart/Einstein的教员
SELECT DISTINCT name 
FROM instructor 
WHERE name NOT IN ('Mozart','Einstein');

-- 4. 多属性IN子查询：统计特定教员授课的选课人数
SELECT COUNT(DISTINCT ID) 
FROM takes 
WHERE (course_id, sec_id, semester, year) IN (SELECT course_id, sec_id, semester, year 
                                              FROM teaches 
                                              WHERE teaches.ID= 10101);

-- 时间点：01:10:42
-- 1. SOME比较：工资高于生物系任意教员的教员
SELECT name 
FROM instructor 
WHERE salary > SOME (SELECT salary 
                     FROM instructor 
                     WHERE dept_name = 'Biology');

-- 2. ALL比较：工资高于生物系所有教员的教员
SELECT name 
FROM instructor 
WHERE salary>ALL (SELECT salary 
                  FROM instructor 
                  WHERE dept_name = 'Biology');

-- 时间点：01:17:35
-- 1. EXISTS存在性查询：2017秋季开课 且 2018春季也开课的课程
SELECT course_id 
FROM section AS S 
WHERE semester ='Fall' AND year=2017 
  AND EXISTS (SELECT * 
              FROM section AS T 
              WHERE semester = 'Spring' AND year = 2018 
                AND S.course_id = T.course_id);

-- 2. NOT EXISTS：2017秋季开课 但 2018春季不开课的课程
SELECT course_id 
FROM section AS S 
WHERE semester ='Fall' AND year=2017 
  AND NOT EXISTS (SELECT * 
                  FROM section AS T 
                  WHERE semester = 'Spring' AND year = 2018 
                    AND S.course_id = T.course_id);

-- 时间点：01:27:25
-- UNIQUE子查询：2017年仅开设一次的课程
SELECT T.course_id 
FROM course AS T 
WHERE UNIQUE(SELECT R.course_id 
             FROM section AS R 
             WHERE T.course_id= R.course_id AND R.year =2017);

-- 时间点：01:28:33
-- 1. FROM子句中子查询（子查询需命名）
SELECT dept_name, avg_salary 
FROM (SELECT dept_name, AVG(salary) AS avg_salary 
      FROM instructor 
      GROUP BY dept_name) AS dept_avg  -- 子查询别名
WHERE avg_salary>42000;

-- 2. FROM子句中子查询（指定列别名）
SELECT dept_name, avg_salary 
FROM (SELECT dept_name, AVG(salary) AS avg_salary 
      FROM instructor 
      GROUP BY dept_name) AS dept_avg (dept_name, avg_salary)  -- 指定列别名
WHERE avg_salary>42000;

-- 时间点：01:32:50
-- 1. WITH临时关系：查询预算最高的系
WITH max_budget(value) AS (SELECT MAX(budget) FROM department) 
SELECT dept_name 
FROM department, max_budget 
WHERE department.budget = max_budget.value;

-- 2. WITH多临时关系：总工资超平均值的系
WITH dept_total (dept_name, value) AS (
    SELECT dept_name, SUM(salary) 
    FROM instructor 
    GROUP BY dept_name
), 
dept_total_avg(value) AS (
    SELECT AVG(value) FROM dept_total
) 
SELECT dept_name 
FROM dept_total, dept_total_avg 
WHERE dept_total.value>dept_total_avg.value;

-- 时间点：01:39:20
-- 标量子查询：统计每个系的教员数量
SELECT dept_name,
       (SELECT COUNT(*) 
        FROM instructor 
        WHERE department.dept_name = instructor.dept_name) AS num_instructors 
FROM department;

/* ======================== 删除/插入/更新操作 ======================== */
-- 时间点：01:46:44
-- 1. 删除教员表所有记录
DELETE FROM instructor;

-- 2. 删除财务系所有教员
DELETE FROM instructor 
WHERE dept_name= 'Finance';

-- 3. 子查询删除：删除Watson大楼所属系的所有教员
DELETE FROM instructor 
WHERE dept_name IN (SELECT dept_name 
                    FROM department 
                    WHERE building = 'Watson');

-- 时间点：01:51:54
-- 1. 插入元组（按字段顺序直接赋值）
INSERT INTO course 
VALUES ('CS-437','Database Systems','Comp.Sci.',4);

-- 2. 插入元组（指定字段赋值，顺序可自定义）
INSERT INTO course (course_id, title, dept_name, credits) 
VALUES('CS-437','Database Systems','Comp.Sci.',4);

-- 3. 插入含NULL值的学生记录
INSERT INTO student 
VALUES('3003','Green','Finance',NULL);

-- 4. 子查询插入：将满足条件的学生转为教员（工资18000）
INSERT INTO instructor 
SELECT ID, name, dept_name, 18000 
FROM student 
WHERE dept_name ='Music' AND tot_cred>144;

-- 时间点：01:56:04
-- 1. 更新所有教员工资（涨5%）
UPDATE instructor 
SET salary = salary*1.05;

-- 2. 条件更新：工资<70000的教员涨5%
UPDATE instructor 
SET salary = salary*1.05 
WHERE salary<70000;

-- 3. 子查询更新：工资低于平均值的教员涨5%
UPDATE instructor 
SET salary = salary*1.05 
WHERE salary<(SELECT AVG(salary) FROM instructor AS i);

-- 4. CASE条件更新：工资≤100000涨5%，否则涨3%
UPDATE instructor 
SET salary = CASE 
                WHEN salary <= 100000 THEN salary*1.05 
                ELSE salary*1.03 
             END;

-- 5. 标量子查询更新：计算学生总学分（排除不及格课程）
UPDATE student 
SET tot_cred = (SELECT SUM(credits) 
                FROM takes 
                JOIN course ON takes.course_id=course.course_id 
                WHERE takes.ID=student.ID 
                  AND takes.grade<>'F' 
                  AND takes.grade IS NOT NULL);

-- 6. CASE条件更新：无选课记录的学生总学分设为NULL
UPDATE student 
SET tot_cred = CASE 
                WHEN (SELECT COUNT(*) FROM takes WHERE takes.ID=student.ID) =0 THEN NULL 
                ELSE tot_cred 
              END;