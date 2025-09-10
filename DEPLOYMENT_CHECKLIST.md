# 🚀 Quick Deployment Checklist

## Pre-Deployment Setup

### 1. Get Your Gemini API Key
- [ ] Go to [Google AI Studio](https://aistudio.google.com/)
- [ ] Create a new API key
- [ ] Copy the API key (you'll need it later)

### 2. Prepare Your Code
- [ ] All files are ready (requirements.txt, app.py, templates, etc.)
- [ ] API key is properly configured in environment variables
- [ ] No sensitive data in code (API keys, passwords, etc.)

## Choose Your Platform

### Option A: Render (Recommended) ⭐
- [ ] Go to [render.com](https://render.com)
- [ ] Sign up with GitHub
- [ ] Click "New +" → "Web Service"
- [ ] Connect your GitHub repository
- [ ] Configure:
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
- [ ] Add environment variables:
  - `GEMINI_API_KEY`: your_api_key_here
  - `FLASK_ENV`: production
- [ ] Click "Create Web Service"
- [ ] Wait for deployment (5-10 minutes)
- [ ] Test your app at the provided URL

### Option B: Railway
- [ ] Go to [railway.app](https://railway.app)
- [ ] Sign up with GitHub
- [ ] Click "New Project" → "Deploy from GitHub repo"
- [ ] Select your repository
- [ ] Add environment variables:
  - `GEMINI_API_KEY`: your_api_key_here
  - `FLASK_ENV`: production
- [ ] Deploy automatically
- [ ] Test your app

### Option C: Fly.io
- [ ] Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
- [ ] Run `fly auth login`
- [ ] Run `fly launch` in your project directory
- [ ] Set environment variables: `fly secrets set GEMINI_API_KEY=your_key`
- [ ] Deploy: `fly deploy`
- [ ] Test your app

## Post-Deployment Testing

### Basic Functionality
- [ ] App loads without errors
- [ ] Can upload a video file
- [ ] Video processing works
- [ ] Can download CSV results
- [ ] AI insights work (if API key is set)

### Performance Testing
- [ ] Test with a small video (5-10 seconds)
- [ ] Check processing time
- [ ] Verify memory usage is reasonable
- [ ] Test with multiple users (if possible)

## Monitoring Setup

### Uptime Monitoring (Prevent App Sleeping)
- [ ] Sign up for [UptimeRobot](https://uptimerobot.com/)
- [ ] Add your app URL
- [ ] Set monitoring interval to 5 minutes
- [ ] This prevents your app from sleeping on free tiers

### Error Monitoring
- [ ] Check platform logs regularly
- [ ] Set up email alerts for errors
- [ ] Monitor API usage and costs

## Optimization Tips

### For Better Performance
- [ ] Use small video files for testing
- [ ] Compress videos before upload
- [ ] Monitor memory usage
- [ ] Consider upgrading if needed

### For Cost Management
- [ ] Monitor API usage (Gemini API)
- [ ] Set up billing alerts
- [ ] Use free tiers efficiently
- [ ] Clean up old files regularly

## Troubleshooting Common Issues

### App Won't Start
- [ ] Check environment variables are set
- [ ] Verify all dependencies are in requirements.txt
- [ ] Check platform logs for errors
- [ ] Ensure port is set to $PORT (not 5000)

### Video Processing Issues
- [ ] Test with smaller video files
- [ ] Check memory limits
- [ ] Verify OpenCV/MediaPipe installation
- [ ] Check file upload limits

### API Errors
- [ ] Verify GEMINI_API_KEY is correct
- [ ] Check API quota and limits
- [ ] Test API key independently
- [ ] Check network connectivity

## Success! 🎉

Once everything is working:
- [ ] Share your app URL with others
- [ ] Document any custom configurations
- [ ] Set up regular backups
- [ ] Plan for scaling if needed

## Quick Commands

### Deploy to GitHub
```bash
git add .
git commit -m "Deploy to free hosting"
git push origin main
```

### Check App Status
- **Render**: Check dashboard at render.com
- **Railway**: Check dashboard at railway.app
- **Fly.io**: Run `fly status`

### View Logs
- **Render**: Click on your service → Logs
- **Railway**: Click on your service → Logs
- **Fly.io**: Run `fly logs`

### Update Environment Variables
- **Render**: Service → Environment → Add Variable
- **Railway**: Variables tab → Add Variable
- **Fly.io**: `fly secrets set KEY=value`

---

**Need Help?** Check the full deployment guide in `FREE_DEPLOYMENT.md` or `DEPLOYMENT.md`

