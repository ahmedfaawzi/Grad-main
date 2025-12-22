-- Create tables for library management system
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    year INTEGER,
    available BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS borrowed_books (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id),
    borrower VARCHAR(255),
    borrow_date DATE DEFAULT CURRENT_DATE,
    return_date DATE
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    full_name VARCHAR(255),
    email VARCHAR(255),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default users
INSERT INTO users (username, password_hash, role, full_name, email) VALUES
('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin', 'System Administrator', 'admin@library.com'),
('librarian', 'a36f7f52dd6a4c1d94dc6543c92e9637a73d8d46e32e4e7c6a0a2d8c07e1b8e2', 'librarian', 'Library Manager', 'librarian@library.com'),
('user', '04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb', 'user', 'Regular User', 'user@library.com')
ON CONFLICT (username) DO NOTHING;

-- Insert sample books
INSERT INTO books (title, author, year, available) VALUES
('The Great Gatsby', 'F. Scott Fitzgerald', 1925, true),
('To Kill a Mockingbird', 'Harper Lee', 1960, true),
('1984', 'George Orwell', 1949, true),
('Pride and Prejudice', 'Jane Austen', 1813, true),
('The Catcher in the Rye', 'J.D. Salinger', 1951, true)
ON CONFLICT DO NOTHING;
