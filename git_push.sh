#!/bin/bash

# Add the GitHub repository as remote origin
git remote add origin git@github.com:newsbubbles/tooler_chat.git

# Push main branch to GitHub
git push -u origin main

# Switch to develop branch and push
git checkout develop
git push -u origin develop

# Switch to feature/testing branch and push
git checkout feature/testing
git push -u origin feature/testing

# Switch back to main branch
git checkout main

echo "All branches have been pushed to GitHub!"
