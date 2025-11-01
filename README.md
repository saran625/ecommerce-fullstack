# E-Commerce Full Stack Application

Complete e-commerce platform with React frontend, Flask backend, MongoDB database, Docker deployment, and AWS hosting.

## 🚀 Quick Start

### Local Development

1. Clone the repository
2. Install Docker and Docker Compose
3. Run: `docker-compose up --build`
4. Access:
   - Frontend: http://localhost
   - Backend API: http://localhost:5000
   - MongoDB: localhost:27017

### Default Credentials
- Admin: admin@ecommerce.com / admin123

## 📦 Tech Stack

- **Frontend**: React 18, React Router, Axios
- **Backend**: Flask, JWT, MongoDB
- **Database**: MongoDB
- **Deployment**: Docker, AWS EC2

## 🛠️ API Endpoints

### Authentication
- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/profile

### Products
- GET /api/products
- GET /api/products/:id
- POST /api/products (Admin)
- PUT /api/products/:id (Admin)

### Cart
- GET /api/cart
- POST /api/cart/add
- DELETE /api/cart/remove/:id

### Orders
- POST /api/orders
- GET /api/orders
- GET /api/orders/:id

## 📝 Environment Variables

### Backend (.env)
```
MONGO_URI=mongodb://mongodb:27017/
DB_NAME=ecommerce_db
JWT_SECRET=your-secret-key
PORT=5000
```

### Frontend (.env)
```
REACT_APP_API_URL=http://localhost:5000/api
```
