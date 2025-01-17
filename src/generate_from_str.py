#!/usr/bin/env python3


import json
import os
import numpy as np
import tensorflow as tf

import model, sample, encoder


class GPT:

    def __init__(self,
                    model_name="774M",
                    seed=None,
                    nsamples=1,
                    batch_size=1,
                    length=None,
                    temperature=1,
                    top_k=0):
        self.batch_size = batch_size
        self.nsamples = nsamples
        self.build_model(model_name=model_name,
                            seed=seed,
                            nsamples=nsamples,
                            batch_size=batch_size,
                            length=length,
                            temperature=temperature,
                            top_k=top_k)

                                    
    def build_model(self,
                    model_name='774M',
                    seed=None,
                    nsamples=1,
                    batch_size=1,
                    length=None,
                    temperature=1,
                    top_k=0,
                    top_p=1,
                    models_dir='models',
                ):
        """
        Interactively run the model
        :model_name=774M : String, which model to use
        :seed=None : Integer seed for random number generators, fix seed to reproduce
        results
        :nsamples=1 : Number of samples to return total
        :batch_size=1 : Number of batches (only affects speed/memory).  Must divide nsamples.
        :length=None : Number of tokens in generated text, if None (default), is
        determined by model hyperparameters
        :temperature=1 : Float value controlling randomness in boltzmann
        distribution. Lower temperature results in less random completions. As the
        temperature approaches zero, the model will become deterministic and
        repetitive. Higher temperature results in more random completions.
        :top_k=0 : Integer value controlling diversity. 1 means only 1 word is
        considered for each step (token), resulting in deterministic completions,
        while 40 means 40 words are considered at each step. 0 (default) is a
        special setting meaning no restrictions. 40 generally is a good value.
        :models_dir : path to parent folder containing model subfolders
        (i.e. contains the <model_name> folder)
        """
        models_dir = os.path.expanduser(os.path.expandvars(models_dir))
        if batch_size is None:
            batch_size = 1
        assert nsamples % batch_size == 0

        enc = encoder.get_encoder(model_name, models_dir)
        hparams = model.default_hparams()
        with open(os.path.join(models_dir, model_name, 'hparams.json')) as f:
            hparams.override_from_dict(json.load(f))

        if length is None:
            length = hparams.n_ctx // 2
        elif length > hparams.n_ctx:
            raise ValueError("Can't get samples longer than window size: %s" % hparams.n_ctx)

        sess = tf.Session()

        context = tf.placeholder(tf.int32, [batch_size, None])
        np.random.seed(seed)
        tf.set_random_seed(seed)
        output = sample.sample_sequence(
            hparams=hparams, length=length,
            context=context,
            batch_size=batch_size,
            temperature=temperature, top_k=top_k, top_p=top_p
        )

        saver = tf.train.Saver()
        ckpt = tf.train.latest_checkpoint(os.path.join(models_dir, model_name))
        saver.restore(sess, ckpt)

        self.sess = sess
        self.enc = enc
        self.hparams = hparams
        self.output = output
        self.context = context


    def generate_from_str(self, input_str: str) -> str:
        """Returns a list of generated text with length equal to nsamples * batch-size"""
        results = []
        context_tokens = self.enc.encode(input_str)
        for _ in range(self.nsamples // self.batch_size):
            out = self.sess.run(self.output, feed_dict={
                self.context: [context_tokens for _ in range(self.batch_size)]
            })[:, len(context_tokens):]
            for i in range(self.batch_size):
                text = self.enc.decode(out[i])
                results.append(text)
        return results

    
