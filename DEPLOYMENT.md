# Sports Analysis App Deployment Guide

This guide covers multiple deployment options for your Flask-based sports analysis application that uses computer vision to analyze push-up form.

## Prerequisites

- Python 3.11+
- Docker (for containerized deployment)
- Git
- A Gemini API key (for AI insights feature)

## Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Quick Start with Docker Compose

1. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

2. **Deploy with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Access the application:**
   - Open http://localhost:5000 in your browser

#### Manual Docker Build

1. **Build the image:**
   ```bash
   docker build -t sports-analyze .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name sports-analyze \
     -p 5000:5000 \
     -e GEMINI_API_KEY=your_api_key_here \
     -v $(pwd)/static:/app/static \
     sports-analyze
   ```

### Option 2: Traditional Server Deployment

#### Using Gunicorn (Production)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export GEMINI_API_KEY=your_api_key_here
   export FLASK_ENV=production
   ```

3. **Run with Gunicorn:**
   ```bash
   gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
   ```

#### Using systemd (Linux)

1. **Create service file** `/etc/systemd/system/sports-analyze.service`:
   ```ini
   [Unit]
   Description=Sports Analysis Flask App
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/your/app
   Environment="PATH=/path/to/your/venv/bin"
   Environment="GEMINI_API_KEY=your_api_key_here"
   Environment="FLASK_ENV=production"
   ExecStart=/path/to/your/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and start the service:**
   ```bash
   sudo systemctl enable sports-analyze
   sudo systemctl start sports-analyze
   ```

### Option 3: Cloud Platform Deployment

#### Heroku

1. **Install Heroku CLI and login**

2. **Create Heroku app:**
   ```bash
   heroku create your-app-name
   ```

3. **Set environment variables:**
   ```bash
   heroku config:set GEMINI_API_KEY=your_api_key_here
   heroku config:set FLASK_ENV=production
   ```

4. **Create Procfile:**
   ```
   web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
   ```

5. **Deploy:**
   ```bash
   git add .
   git commit -m "Deploy to Heroku"
   git push heroku main
   ```

#### Railway

1. **Connect your GitHub repository to Railway**

2. **Set environment variables in Railway dashboard:**
   - `GEMINI_API_KEY`: your_api_key_here
   - `FLASK_ENV`: production

3. **Deploy automatically on git push**

#### DigitalOcean App Platform

1. **Create a new app in DigitalOcean**

2. **Connect your GitHub repository**

3. **Configure environment variables:**
   - `GEMINI_API_KEY`: your_api_key_here
   - `FLASK_ENV`: production

4. **Deploy**

#### AWS EC2

1. **Launch an EC2 instance (Ubuntu 22.04 LTS)**

2. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv nginx
   ```

3. **Clone and setup your app:**
   ```bash
   git clone your-repo-url
   cd sports_analyze
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure Nginx:**
   ```bash
   sudo nano /etc/nginx/sites-available/sports-analyze
   ```
   
   Add this configuration:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

5. **Enable the site and restart Nginx:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/sports-analyze /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

6. **Run your app with systemd (see systemd section above)**

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GEMINI_API_KEY` | Google Gemini API key for AI insights | Yes | - |
| `GEMINI_MODEL` | Gemini model to use | No | gemini-1.5-flash |
| `FLASK_ENV` | Flask environment | No | development |
| `PORT` | Port to run the app on | No | 5000 |

## Security Considerations

1. **Never commit API keys to version control**
2. **Use environment variables for sensitive data**
3. **Enable HTTPS in production (use Let's Encrypt)**
4. **Set up proper firewall rules**
5. **Regular security updates**

## Monitoring and Maintenance

1. **Set up log monitoring**
2. **Monitor disk space** (video uploads can be large)
3. **Set up health checks**
4. **Regular backups of uploaded data**
5. **Monitor API usage and costs**

## Troubleshooting

### Common Issues

1. **OpenCV/MediaPipe installation issues:**
   - Use the provided Dockerfile which includes all system dependencies
   - For manual installation, ensure all OpenCV dependencies are installed

2. **Memory issues with large videos:**
   - Increase worker timeout in Gunicorn
   - Consider video compression before processing
   - Monitor server memory usage

3. **API key issues:**
   - Verify the GEMINI_API_KEY environment variable is set correctly
   - Check API key permissions and quotas

4. **File upload issues:**
   - Ensure upload directories have proper permissions
   - Check file size limits in your web server configuration

### Performance Optimization

1. **Use multiple Gunicorn workers** for better concurrency
2. **Implement video compression** before processing
3. **Add caching** for frequently accessed data
4. **Use a CDN** for static files
5. **Consider using Redis** for session storage in production

## Scaling Considerations

For high-traffic deployments:

1. **Use a load balancer** (nginx, HAProxy)
2. **Implement horizontal scaling** with multiple app instances
3. **Use external storage** (S3, Google Cloud Storage) for video files
4. **Implement database** for session persistence
5. **Use message queues** for video processing tasks

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review application logs
3. Verify environment variables are set correctly
4. Test with a simple video file first

