# Use Node.js official image as base
FROM node:18-alpine

# Set working directory in container
WORKDIR /app

# Copy package files first (for better layer caching)
COPY package*.json ./

# Install dependencies
RUN npm install

# Install serve globally
RUN npm install -g serve

# Copy the rest of the application code
COPY . .

# Build the React app
RUN npm run build

# Expose port 34140
EXPOSE 34140

# Start the application using serve
CMD ["serve", "-s", "build", "-p", "34140"]



# FROM node:18-alpine as build

# WORKDIR /app

# # Install dependencies
# COPY package.json package-lock.json* ./
# RUN npm ci

# # Copy application code
# COPY . .

# # Build the application
# RUN npm run build

# RUN npm install -g serve

# RUN npm serve -s build -l 34140

# # Production stage
# # FROM nginx:alpine

# # Copy built assets from build stage
# # COPY --from=build /app/build /usr/share/nginx/html

# # # Copy nginx configuration as a template
# # COPY nginx.conf /etc/nginx/conf.d/default.template

# # # Copy and make entrypoint script executable
# # COPY docker-entrypoint.sh /docker-entrypoint.sh
# # RUN chmod +x /docker-entrypoint.sh

# # # Install envsubst for template processing
# # RUN apk add --no-cache gettext

# # # Expose port 80
# # EXPOSE 80

# # Set entrypoint to our script
# # ENTRYPOINT ["/docker-entrypoint.sh"]

# # Start nginx
# # CMD ["nginx", "-g", "daemon off;"]

