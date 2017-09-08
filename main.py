import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests

from tqdm import tqdm
import math


"""Semantic Segmentation with Fully Convolutional Networks

based on https://people.eecs.berkeley.edu/~jonlong/long_shelhamer_fcn.pdf
"""

# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), \
    'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    vgg_tag = 'vgg16'
    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)
    graph = tf.get_default_graph()

    vgg_input_tensor_name = 'image_input:0'
    t1 = graph.get_tensor_by_name(vgg_input_tensor_name)
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    t2 = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    t3 = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    t4 = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    vgg_layer7_out_tensor_name = 'layer7_out:0'
    t5 = graph.get_tensor_by_name(vgg_layer7_out_tensor_name)

    return t1, t2, t3, t4, t5



def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer7_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer3_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    conv_1x1 = tf.layers.conv2d(vgg_layer7_out, num_classes, kernel_size=1,
                                strides=(1,1), padding='SAME',
                                kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    # in the paper they 'initialise to bilinear interpolation'. here we do random initialization
    up4 = tf.layers.conv2d_transpose(conv_1x1, 512,
                                        kernel_size=4, strides=2, padding='SAME',
                                        kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    skip4 = tf.add(up4, vgg_layer4_out)
    up3 = tf.layers.conv2d_transpose(skip4, 256,
                                        kernel_size=4, strides=2, padding='SAME',
                                        kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    skip3 = tf.add(up3, vgg_layer3_out)
    output = tf.layers.conv2d_transpose(skip3, num_classes,
                                        kernel_size=16, strides=8, padding='SAME',
                                        kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    return output


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    # TODO: use weighted loss based on how our classes are represented?
    cross_entropy_loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=correct_label))
    optimizer = tf.train.AdamOptimizer(learning_rate).minimize(cross_entropy_loss)
    return logits, optimizer, cross_entropy_loss


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    # TODO: Implement function
    n_samples = 289
    keep_probability_value = 0.9
    learning_rate_value = 0.001
    sess.run(tf.global_variables_initializer())
    for epoch in range(epochs):
        # running optimization in batches of training set
        n_batches = int(math.ceil(float(n_samples) / batch_size))
        batches_pbar = tqdm(get_batches_fn(batch_size),
                            desc='Train Epoch {:>2}/{}'.format(epoch + 1, epochs),
                            unit='batches',
                            total=n_batches)
        for images, labels in batches_pbar:
              feed_dict = {input_image: images,
                           correct_label: labels,
                           keep_prob: keep_probability_value,
                           learning_rate: learning_rate_value}
              _, loss = sess.run([train_op, cross_entropy_loss], # , self._summaries
                                 feed_dict=feed_dict)
              print("loss={}".format(loss))
              break
              # write training summaries for tensorboard every so often
              #step = self._global_step.eval(session=self._session)
              #if step % 5 == 0:
              #    summary_writer.add_summary(summaries, global_step=step)

      #tf.Print(tensor, [tf.shape(tensor)])


def run():
    num_classes = 2
    image_shape = (160, 576)
    data_dir = './data'
    runs_dir = './runs'

    #tests.test_for_kitti_dataset(data_dir)
    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)
    # TODO: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    #  https://www.cityscapes-dataset.com/

    config = tf.ConfigProto(log_device_placement=False, device_count = {'GPU': 0})
    config.gpu_options.allow_growth = True
    config.gpu_options.per_process_gpu_memory_fraction = 0.5
    with tf.Session(config=config) as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        #tests.test_load_vgg(load_vgg, tf)
        image_input, keep_prob, l3, l4, l7 = load_vgg(sess, vgg_path)
        correct_label = tf.placeholder(tf.float32, name='label_input')

        #tests.test_layers(layers)
        output = layers(l3, l4, l7, num_classes)

        #tests.test_optimize(optimize)
        learning_rate = tf.placeholder(tf.float32, name="learning_rate")
        logits, optimizer, cross_entropy_loss = optimize(output, correct_label, learning_rate, num_classes)

        # TODO: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        #tests.test_train_nn(train_nn)
        epochs = 1
        batch_size = 5
        train_nn(sess, epochs, batch_size, get_batches_fn, optimizer, cross_entropy_loss,
                 image_input, correct_label, keep_prob, learning_rate)

        # TODO: Save inference data using helper.save_inference_samples
        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, image_input)

        # TODO: Apply the trained model to a video


if __name__ == '__main__':
    run()
