-- 【教授 01:02:08 - 01:18:08 核心演示内容】
-- 对应课程：Create Table 与 Updates to tables 实操


-- ---------------------------------------------
-- 教授 01:02:08：Create Table 基础语法演示
-- ---------------------------------------------
-- 注意：为避免与上方完整 instructor 表冲突
create table instructor (
    ID char(5),
    name varchar(20),
    dept_name varchar(20),
    salary numeric(8,2)
);

-- ---------------------------------------------
-- 教授 01:07:06
-- ---------------------------------------------

-- 1. Insert 插入数据演示（教授 01:07:34）
insert into instructor values ('10211','Smith','Biology',66000);

-- 验证插入结果（教授 01:08:42）
select * from instructor;

-- 2. 创建测试表 test（教授 01:11:34）
create table test (
    id varchar(10),
    name varchar(10)
);

-- 向 test 表插入数据
insert into test values ('11111','CST');

-- 验证 test 表数据
select * from test;

-- 再插入一条 test 数据
insert into test values ('22222','database system');

-- 验证两条数据
select * from test;

-- 3. Delete 删除数据演示（教授 01:12:18）
-- 删除 test 表所有数据（表结构保留）
delete from test;

-- 验证删除后 test 表为空
select * from test;

-- 验证 test 表结构仍存在（教授 01:13:12）
.schema test

-- 4. Drop Table 删除表演示（教授 01:13:54）
drop table test;

-- 验证 test 表已被彻底删除
.schema test

-- 5. Alter 修改表结构演示（教授 01:14:44）
-- 重新创建 test 表
create table test (
    id varchar(10),
    name varchar(10)
);

-- 为 test 表添加新属性 address（教授 01:15:30）
alter table test add address varchar(10);

-- 验证新属性已添加
.schema test

-- 删除 test 表的 id 属性（教授 01:15:50）
alter table test drop id;

-- 验证 id 属性已删除
.schema test



-- 三、基础查询操作（SELECT 核心用法）


-- 1. 简单查询：查询所有教员的所有信息
select * from instructor;

-- 2. 指定属性查询：查询所有教员的姓名
select name from instructor;

-- 3. 去重查询：查询所有不重复的系名
select distinct dept_name from instructor;

-- 4. 保留重复查询：显式保留所有系名（默认行为）
select all dept_name from instructor;

-- 5. 算术表达式查询：查询教员的月薪（原工资除以12）
select ID, name, salary/12 as monthly_salary from instructor;

-- 6. 字面量查询：直接输出常量（生成临时表）
select '437' as FOO;

-- 7. WHERE 条件查询：查询计算机系的教员姓名
select name from instructor where dept_name = 'Comp.Sci.';

-- 8. 多条件查询：查询计算机系且工资大于70000的教员姓名
select name from instructor where dept_name = 'Comp.Sci.' and salary>70000;

-- 9. 字符串模糊匹配：查询姓名包含 "zar" 的教员
select name from instructor where name like '%zar%';

-- 10. 单字符匹配：查询姓名前两位任意、后三位为 "and" 的教员
select name from instructor where name like '__and';

-- 11. 多表查询（笛卡尔积+筛选）：查询授课教员的姓名和对应课程ID
-- 对应课程中 "Find the names of all instructors who have taught some course" 示例
select name, course_id from instructor, teaches where instructor.ID = teaches.ID;

-- 12. 笛卡尔积演示（对应课程中 instructor × teaches 示例）
-- 注意：会产生大量数据，仅作演示理解
select * from instructor, teaches;


-- ==============================================
-- 课程思考题：查询没有教过课的教员姓名
-- ==============================================


-- 解法一：使用 NOT IN + 子查询
-- 逻辑：先找出所有教过课的教员ID，再筛选出不在这个列表里的教员
select name
from instructor
where ID not in (
    select distinct ID
    from teaches
);

-- 解法二：使用 LEFT JOIN + IS NULL 左连接
-- 逻辑：以 instructor 为左表做左连接，teaches 表中匹配不到的数据会显示为 NULL
select name
from instructor
left join teaches on instructor.ID = teaches.ID
where teaches.ID is null;




