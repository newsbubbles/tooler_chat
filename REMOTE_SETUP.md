# Setting Up Remote Repository

To connect this local repository to the GitHub repository, run the following command:

```bash
git remote add origin git@github.com:newsbubbles/tooler_chat.git
```

Then push your code to GitHub:

```bash
# Push main branch
git push -u origin main

# Push develop branch
git checkout develop
git push -u origin develop

# Push feature branch
git checkout feature/testing
git push -u origin feature/testing
```

This will set up tracking for all branches and push your code to GitHub.
