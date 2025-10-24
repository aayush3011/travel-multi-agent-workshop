#!/bin/bash
echo "🧹 Cleaning Angular cache..."
rm -rf .angular/cache
rm -rf node_modules/.cache
echo "✨ Cache cleaned!"
echo ""
echo "🚀 Starting dev server..."
npm start
