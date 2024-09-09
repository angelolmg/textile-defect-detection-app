# Use a Node.js base image
FROM node:16

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Expose port 4200 for the Angular app
EXPOSE 4200

# Start the Angular app
CMD ["ng", "serve", "--host", "0.0.0.0"]
