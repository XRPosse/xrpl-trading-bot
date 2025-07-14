# Troubleshooting Guide

## Common Issues

### Installation Problems

**Issue**: Dependencies won't install
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Runtime Errors

**Issue**: Cannot connect to database
- Check database is running
- Verify connection string
- Check network/firewall

**Issue**: API returns 401
- Check authentication token
- Verify token hasn't expired
- Ensure correct permissions

### Build Failures

**Issue**: Build fails with memory error
```bash
# Increase Node memory
NODE_OPTIONS=--max-old-space-size=4096 npm run build
```

## Debug Mode

Enable debug logging:
```bash
DEBUG=app:* npm run dev
```

## Getting Help

1. Check existing issues
2. Review documentation
3. Ask in discussions

---
Last updated: [Date]