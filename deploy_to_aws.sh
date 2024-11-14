#!/bin/bash

# Define AWS server information
AWS_USER="ubuntu"
AWS_HOST="16.171.250.172"
PEM_PATH="G:/freelance/jamey sir/backend/voiceagent.pem"
DEPLOY_DIR="~/projectdir"
ZIP_FILE="deployment.zip"
STATIC_DIR="$DEPLOY_DIR/staticfiles"  # Static files directory inside the project

# Step 1: Upload the ZIP file to the AWS server
echo "Uploading ZIP archive to AWS server..."
scp -i "$PEM_PATH" $ZIP_FILE "$AWS_USER@$AWS_HOST:~/"

# Step 2: Rename the current deployment directory on the server
echo "Renaming current deployment directory on AWS server..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    if [ -d '$DEPLOY_DIR' ]; then
        mv $DEPLOY_DIR ${DEPLOY_DIR}_$(date +%Y%m%d_%H%M%S)
    fi
"

# Step 3: Unzip the new code in the project directory on the server
echo "Unzipping new code on AWS server..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    mkdir -p $DEPLOY_DIR && unzip -o ~/deployment.zip -d $DEPLOY_DIR && rm ~/deployment.zip
"

# Step 4: Run Django collectstatic to gather static files in the correct directory
echo "Running Django collectstatic to gather static files..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    cd $DEPLOY_DIR && source ~/venv/bin/activate && python manage.py collectstatic --noinput
"

# Step 5: Set ownership of the static files to www-data:www-data
echo "Setting ownership of static files to www-data:www-data..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    sudo chown -R www-data:www-data $STATIC_DIR
"

# Step 6: Set correct permissions for static files and directories
echo "Setting permissions for static files..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    sudo find $STATIC_DIR -type d -exec chmod 755 {} \;   # Directories
    sudo find $STATIC_DIR -type f -exec chmod 644 {} \;   # Files
"

# Step 7: Restart Gunicorn (or your WSGI server)
echo "Restarting Gunicorn..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    sudo systemctl restart gunicorn
"

# Step 8: Restart Daphne (or your ASGI server)
echo "Restarting Daphne..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    sudo systemctl restart daphne
"

# Step 9: Reload Nginx
echo "Reloading Nginx..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    sudo systemctl reload nginx
"

# Step 10: Reload systemd daemon (only if necessary)
echo "Reloading systemd daemon..."
ssh -i "$PEM_PATH" "$AWS_USER@$AWS_HOST" "
    sudo systemctl daemon-reload
"

# Step 11: Clean up local ZIP file (optional)
# Uncomment the next line if you want to delete the local ZIP file after upload
# echo "Cleaning up local ZIP file..."
# rm $ZIP_FILE

echo "Deployment complete."

