FROM python:3.8-slim
WORKDIR /app
COPY ./app /app 
RUN pip3 install -r requirements.txt
ENV PATH /app:$PATH
EXPOSE 8000
ENTRYPOINT ["python3"]
CMD ["app.py"]
