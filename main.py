import re
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold
import numpy as np
from tensorflow import keras
from keras import backend as K
import matplotlib.pyplot  as plt
from sklearn.metrics import classification_report


def rmse(y_true, y_pred):
    return K.sqrt(K.mean(K.square(y_pred - y_true)))
    
def plot(train_acc, test_acc, train_loss, test_loss, label):
    plt.plot(train_acc)
    plt.plot(test_acc)
    plt.title(label + ' - Accuracy')
    plt.ylabel('accuracy')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')
    plt.show()

    # summarize history for loss
    plt.plot(train_loss)
    plt.plot(test_loss)
    plt.title(label + ' - Loss')
    plt.ylabel('loss')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')
    plt.show()

def read_file(filename):
    arr = []

    try:
        with open(filename, 'r') as file:
            lines = file.readlines()
            for line in lines:
                arr.append(line.split(',')[0])
    except FileNotFoundError:
        raise "Could not read file:" + filename
        
    return arr

def read_data(fn1 , fn2, docs=None):
    
    try:
        with open(fn1) as fd, open(fn2) as fl:
            X = []
            y = []
            words = []
            cnt = 0

            # safe mode
            if docs is None:
                docs = 10

            while True:

                # get each line from the files
                data_line = fd.readline().strip('\n')
                label_line = fl.readline().strip('\n') 
                
                # check if EOF
                if len(data_line) == 0:
                    return X, y

                # labels
                y.append(label_line.split(' '))

                # convert to list and throw 2 first elem
                temp = data_line.split(' ')

                # get every word to create sentece
                # The total of sentences create a document
                for char in temp:
                    if not re.findall('<(.*?)>', char):
                        words.append(char)

                # append document
                X.append(' '.join(words))

                words.clear()

                cnt += 1
                if cnt >= docs:
                    return X, y
                    
    except FileNotFoundError:
        raise "Count not read file"

def get_model(n_inputs, n_outputs, loss_f, n_hidden1, n_hidden2, lr, m, wd):
    model = keras.models.Sequential()
    model.add(keras.Input(shape=(n_inputs,)))
    model.add(keras.layers.Dense(n_hidden1, activation='relu', kernel_regularizer=keras.regularizers.L2(wd)))
    model.add(keras.layers.Dense(n_hidden2, activation='relu', kernel_regularizer=keras.regularizers.L2(wd)))
    model.add(keras.layers.Dense(n_outputs, activation='sigmoid'))

    opt = keras.optimizers.SGD(learning_rate=lr, momentum=m)
    model.compile(optimizer=opt, loss=loss_f, metrics=['acc', keras.metrics.BinaryAccuracy(threshold=0.5), rmse])

    return model

def evaluate_model(X, y):
    scores = []
    train_acc, test_acc, train_loss, test_loss = [], [], [], []

    es = keras.callbacks.EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=20)

    # train - test data split 
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Split the data to training and testing data 5-Fold
    kfold = KFold(n_splits=2, shuffle=True)
    for i, (train, test) in enumerate(kfold.split(X_train)):

        # create model
        # input-demensions, output-dims, loss-function, hidden1, hidden2, learning-rate, momentum, weight-decay
        model = get_model(X.shape[1], y.shape[1], 'binary_crossentropy', 20, 20, 0.01, 0.6, 0.1)
   
        # Fit model
        h = model.fit(X_train[train], y_train[train], validation_data=(X_train[test], y_train[test]), epochs=150, batch_size=64, callbacks=[], verbose=0)

        # store for each fold the history
        train_acc.append(h.history['binary_accuracy'])
        test_acc.append(h.history['val_binary_accuracy'])
        train_loss.append(h.history['loss'])
        test_loss.append(h.history['val_loss'])

        # evaluate model and store
        scores.append(model.evaluate(X_train[test], y_train[test], verbose=0)[1])
        print(f'Fold {i}:  {scores[i]}')

    # average folds
    train_acc = np.average(train_acc, axis=0)
    test_acc = np.average(test_acc, axis=0)
    train_loss = np.average(train_loss, axis=0)
    test_loss = np.average(test_loss, axis=0)
    
    # plot averaged folds
    plot(train_acc, test_acc, train_loss, test_loss, 'CE')
        
    # make predict to unseen data
    yhat = model.predict(X_test)    
    yhat = yhat.round()

    print(classification_report(y_test, yhat))

def plot_regularizer(X, y):
    values = [1e-3, 1e-2, 1e-1, 5e-1, 9e-1]
    all_train, all_test = [], []
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    es = keras.callbacks.EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=20)
    # Split the data to training and testing data 5-Fold
    for param in values:
        # define model
        model = get_model(X.shape[1], y.shape[1], 'binary_crossentropy', 20, 20, param)
        # fit model
        model.fit(X_train, y_train, epochs=200, batch_size=64, verbose=1)
        # evaluate the model
        train_acc = model.evaluate(X_train, y_train, verbose=1)
        test_acc = model.evaluate(X_test, y_test, verbose=1)
        print('Param: %f, Train: %.3f, Test: %.3f' % (param, train_acc[1], test_acc[1]))
        all_train.append(train_acc[1])
        all_test.append(test_acc[1])

    # plot train and test means
    plt.semilogx(values, all_train, label='train', marker='o')
    plt.semilogx(values, all_test, label='test', marker='o')
    plt.legend()
    plt.show()

def get_model_embeddings(voc_size, n_inputs, n_outputs, loss_f, n_hidden1):
        model = keras.models.Sequential()
        model.add(keras.layers.Embedding(voc_size, 32, input_length=n_inputs, name='embedding'))
        model.add(keras.layers.Flatten())
        model.add(keras.layers.Dense(n_hidden1, activation='relu'))
        model.add(keras.layers.Dense(n_outputs, activation='sigmoid'))
        opt = keras.optimizers.SGD(learning_rate=1e-2)
        model.compile(optimizer=opt, loss=loss_f, metrics=['acc', keras.metrics.BinaryAccuracy(threshold=0.5)])
        
        return model

def get_model_lstm(voc_size, n_inputs, n_outputs, lstm_units, loss_f):
        model = keras.models.Sequential()
        model.add(keras.layers.Embedding(voc_size, 32, input_length=n_inputs, name='embedding'))
        model.add(keras.layers.LSTM(lstm_units, keras.layers.Dropout(0.5), input_shape=(n_inputs, 32), return_sequences=True))
        model.add(keras.layers.LSTM(lstm_units, keras.layers.Dropout(0.5)))
        model.add(keras.layers.Dense(n_outputs, activation='sigmoid'))
        opt = keras.optimizers.SGD(learning_rate=1e-1)
        model.compile(optimizer=opt, loss=loss_f, metrics=['acc', keras.metrics.BinaryAccuracy(threshold=0.5), rmse])
        print(model.summary())
        return model

def evaluate_embeddings_lstm(X, y, both=False):

    # convert docs to one_hot
    encoded_docs = [doc.split(' ') for doc in X]

    # maximum doc length is going to form the input size of NN
    max_len = len(max(encoded_docs, key=len))

    # vocabulary size
    vocab_size = 8520

    # padd encoded docs to match max length
    padded_docs = keras.preprocessing.sequence.pad_sequences(encoded_docs, maxlen=max_len, padding='post')

    if both:
        # get lstm_embeddings model
        model = get_model_lstm(vocab_size, max_len, 20, 64, 'binary_crossentropy')
    else:    
        # get embeddings model
        model = get_model_embeddings(vocab_size, max_len, 20, 'binary_crossentropy', 20)

    # split data
    X_train, X_test, y_train, y_test = train_test_split(padded_docs, y, test_size=0.2, random_state=42)
    
    # fit
    h = model.fit(X_train, y_train, validation_split=0.33, epochs=50, batch_size=128, verbose=1)

    # evaluate with unseen data
    print(model.evaluate(X_test, y_test))

    plot(h.history['binary_accuracy'], h.history['val_binary_accuracy'], h.history['loss'], h.history['val_loss'], 'CE')


def main():

    # load data
    X_raw, y_raw = read_data('Data/train-data.dat', 'Data/train-label.dat', 8250)
    y = np.asarray(y_raw, dtype=int)

    # get choice for model
    print('1. BoW\n2. Word Embeddings\n3. LSTM')
    choice = int(input('Choice: '))

    if choice == 1:
        # create corpus 
        voc = [str(i) for i in range(8520)]

        # tranform X, y to numpy arrays
        X_bow = CountVectorizer(vocabulary=voc).transform(X_raw).toarray()

        ################ CENTERING  ##########################################
        # row_means = np.mean(X, axis=1)
        # X = np.subtract(X, row_means.reshape((row_means.shape[0], 1)))
        
        ################ NORMALIZATION ########################################
        X = MinMaxScaler().fit_transform(X_bow)

        ################ STANDARDIZATION ########################################
        # X = StandardScaler().fit_transform(X)

        evaluate_model(X, y)

    elif choice == 2:
        evaluate_embeddings_lstm(X_raw, y)

    elif choice == 3:
        evaluate_embeddings_lstm(X_raw, y, True)


main()