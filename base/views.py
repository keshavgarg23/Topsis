from django.shortcuts import render
from django.core.mail import EmailMessage
from django.conf import settings


import threading
import pandas as pd
import numpy as np
import csv
from io import StringIO
# Create your views here.


def home(request):
    if(request.method == 'POST'):
        file = request.FILES["file"]    #get file
        if file.name.split('.')[-1]!='csv':     # check csv
            return render(request,'base/msg.html',{'msg':'Please upload a csv file(with .csv extension'})
        # data = file.read().decode("utf-8")  #get file content into a string
        df = pd.read_csv(file)
        weights = request.POST.get("weights")
        impacts = request.POST.get("impacts")
        email = request.POST.get("email")
        [msg,success,df] = get_score(df,weights,impacts)
        if(success):
            t1 = threading.Thread(target = send_csv,args = (df,email,file.name))
            t1.start()
        return render(request,'base/msg.html',{'msg':msg})
    return render(request,'base/form.html')





def send_csv(df,email,name):
    attachment = StringIO()
    writer = csv.writer(attachment)
    writer.writerow([col for col in df.columns])    #put col names
    
    for i in range(df.shape[0]):
        writer.writerow(df.iloc[i,:].values)
    
    subject = "Topsis score and rank result file for "+name
    body = "This email contains the result of "+name+" file uploaded by you."

    email_msg = EmailMessage(
        subject,
        body,
        settings.EMAIL_HOST_USER,
        [email]
    )
    email_msg.attach('result-'+name+'.csv',attachment.getvalue(),'text/csv')
    email_msg.send(fail_silently=True)
    


def get_score(dataframe,weights,impacts):

    weights = [float(x) for x in weights.split(',')]
    impacts = impacts.split(',')

    ## check for column count>3
    if dataframe.shape[1]<3:
        return ["Dataset must have atleast 3 columns(first column being name)!",0,None]
    ## check for non numeric columns
    for i in range(1,dataframe.shape[1]):
        if (dataframe.dtypes[i]=='object'):
            return ["Dataset has non numeric columns. Please make them numeric and enter the weights and impacts accordingly!",0,None]

    df = dataframe.iloc[:,1:].values
    df = df.astype('float64')

    ## check for correct weights and impacts entered
    if df.shape[1]!=len(weights):
        return ["Enter the correct number of weights!",0,None]
    if df.shape[1]!=len(impacts):
        return ["Enter the correct number of impacts!",0,None]



    # calculating the root of sum of squares for each column
    sum_sq = []
    for i in range(df.shape[1]):
        sum_sq.append(np.sqrt(np.sum(df[:,i]**2)))



    # normalisation and weight multiplication
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            df[i,j]=df[i,j]/sum_sq[j] * weights[j]



    # calculating the ideal best and ideal worst lists
    ideal_best = []
    ideal_worst = []

    for i in range(df.shape[1]):
        if impacts[i]=='+':
            ideal_best.append(np.max(df[:,i]))
            ideal_worst.append(np.min(df[:,i]))
        elif impacts[i]=='-':
            ideal_best.append(np.min(df[:,i]))
            ideal_worst.append(np.max(df[:,i]))
        else: # error handling
            return ["Impacts must be either + or -!",0,None]
            





    # calculating the distance from best and worst
    dist_from_best = []
    dist_from_worst = []

    for i in range(df.shape[0]):
        d_b = np.sqrt(np.sum((ideal_best-df[i,:])**2))
        dist_from_best.append(d_b)
        d_w = np.sqrt(np.sum((ideal_worst-df[i,:])**2))
        dist_from_worst.append(d_w)




    # calculating the score values
    score = [dist_from_worst[i]/(dist_from_worst[i]+dist_from_best[i]) for i in range(len(dist_from_best))]




    # calculating the ranks
    sorted_score = sorted(score,reverse=True)
    rank = [sorted_score.index(x)+1 for x in score]

    dataframe['Topsis Score']=score
    dataframe['Rank'] = rank

    #email
    return ["Result will be sent to given email shortly!",1,dataframe]

    


