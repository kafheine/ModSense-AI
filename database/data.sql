CREATE DATABASE IF NOT EXISTS modsense_db;
USE modsense_db;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS ai_chat_logs;
DROP TABLE IF EXISTS content_moderations;
DROP TABLE IF EXISTS post_likes;
DROP TABLE IF EXISTS post_comments;
DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS community_members;
DROP TABLE IF EXISTS communities;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
    user_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','user') NOT NULL DEFAULT 'user',
    status ENUM('active','inactive') NOT NULL DEFAULT 'active',
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE categories (
    category_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    category_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (category_id),
    UNIQUE KEY uq_category_name (category_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE communities (
    community_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    category_id INT UNSIGNED DEFAULT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255) NOT NULL,
    about TEXT,
    status ENUM('active','inactive') NOT NULL DEFAULT 'active',
    created_by INT UNSIGNED DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (community_id),
    UNIQUE KEY uq_community_name (name),
    CONSTRAINT fk_community_category
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_community_creator
        FOREIGN KEY (created_by) REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE community_members (
    membership_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    community_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (membership_id),
    UNIQUE KEY uq_user_community (community_id, user_id),
    CONSTRAINT fk_member_community
        FOREIGN KEY (community_id) REFERENCES communities(community_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_member_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE posts (
    post_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    community_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id),
    CONSTRAINT fk_post_community
        FOREIGN KEY (community_id) REFERENCES communities(community_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_post_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE post_comments (
    comment_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    post_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    parent_comment_id INT UNSIGNED DEFAULT NULL,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (comment_id),
    CONSTRAINT fk_comment_post
        FOREIGN KEY (post_id) REFERENCES posts(post_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comment_parent
        FOREIGN KEY (parent_comment_id) REFERENCES post_comments(comment_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE post_likes (
    like_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    post_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (like_id),
    UNIQUE KEY uq_post_user_like (post_id, user_id),
    CONSTRAINT fk_like_post
        FOREIGN KEY (post_id) REFERENCES posts(post_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_like_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE content_moderations (
    moderation_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    post_id INT UNSIGNED NOT NULL,
    flag_reason VARCHAR(100) NOT NULL,
    risk_level ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
    ai_score DECIMAL(5,2) NOT NULL,
    status ENUM('pending','approved','removed') NOT NULL DEFAULT 'pending',
    reviewed_by INT UNSIGNED DEFAULT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (moderation_id),
    UNIQUE KEY uq_moderation_post (post_id),
    CONSTRAINT fk_moderation_post
        FOREIGN KEY (post_id) REFERENCES posts(post_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_moderation_reviewer
        FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ai_chat_logs (
    chat_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    user_query TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chat_id),
    CONSTRAINT fk_chat_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO users
(first_name,last_name,email,password_hash,role,status)
VALUES
('Admin','User','admin@aicommunity.com','Admin@123','admin','active'),
('Demo','User','user@aicommunity.com','User@123','user','active'),
('Alex','Johnson','alex@example.com','Pass@123','user','active'),
('Sarah','Wilson','sarah@example.com','Pass@123','user','active'),
('Michael','Lee','michael@example.com','Pass@123','admin','active'),
('Emily','Davis','emily@example.com','Pass@123','user','inactive')
('Tiya','Smith','tiya321@gmail.com','tiya11@','user','active'),
('Test','User','test@example.com','Test@123','user','active');

INSERT INTO categories (category_name)
VALUES ('Technology'),('Development'),('Data'),('Design'),('Arts & Creativity'),('Photography & Creativity');

INSERT INTO communities
(category_id,name,description,about,status,created_by)
VALUES
(1,'AI & Technology','Discussions about AI and technology.',
 'A community for artificial intelligence and technology discussions.','active',1),
(2,'Web Development','Web development discussions.',
 'Discuss web technologies, programming and best practices.','active',1),
(3,'Data Science','Data science and analytics.',
 'Discuss data science, analytics, machine learning and data-driven solutions.','active',1),
(4,'Design & Creativity','Design ideas and creative discussions.',
 'A creative space for UI/UX, graphics and digital products.','inactive',1),
(5,'Arts & Creativity','Artistic expressions and creative discussions.',
 'A community for artists, designers and creative professionals.','active',1),
(6,'Photography & Creativity','Photography and creative discussions.',
 'A community for photographers and creative professionals.','active',1);

INSERT INTO community_members (community_id,user_id)
VALUES
(1,2),(2,2),(1,3),(1,4),(1,8),(3,8);

INSERT INTO posts (community_id,user_id,title,content)
VALUES
(1,3,'How is AI changing software development?',
 'AI tools are becoming an important part of modern software development. Developers use AI assistants for coding, debugging, documentation and learning.'),
(2,4,'Best technologies to learn for web development',
 'Which technologies should beginners focus on when starting their web development journey?'),
(3,3,'Getting started with Data Science',
 'I am starting my data science journey. What should I learn first?'),
 (3,8,'The Future of Data Science with AI',
 'AI is transforming data science by making data analysis, prediction, and visualization faster and more efficient. Machine learning models can identify patterns in large datasets and help organizations make better data-driven decisions.');

INSERT INTO post_comments
(post_id,user_id,parent_comment_id,comment_text)
VALUES
(1,3,NULL,'AI tools have definitely made coding and debugging faster.'),
(1,4,1,'I agree. They are especially useful when learning new technologies.'),
(1,5,NULL,'Developers should still understand the code generated by AI.'),
(1,8,NULL,'I think AI tools are very helpful for developers, especially for finding errors and understanding difficult concepts.'),
(1,8,1,'I agree, Alex. AI tools can be very helpful, but developers should still understand the code and use AI as a support rather than relying on it completely.'),
(1,8,3,'I agree, Michael. Understanding the code generated by AI is really important because it helps developers identify errors, make changes, and build better solutions confidently.'),
(1,8,NULL,'I think the best way to use AI in development is as a learning assistant that helps us explore ideas while we continue to solve problems ourselves.');

 INSERT INTO post_likes
(post_id,user_id)
VALUES
(1,8);

INSERT INTO content_moderations
(post_id,flag_reason,risk_level,ai_score,status)
VALUES
(1,'Promotional content','High',92,'pending'),
(2,'Inappropriate language','Medium',68,'pending'),
(3,'Spam link','High',88,'pending');

SET FOREIGN_KEY_CHECKS = 1;
