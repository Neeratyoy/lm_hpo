"""
Defines a training function to take a configuration, train, and return results.
"""

import wandb

from data.data_prep_tinyshakespeare import get_batch, prepare_shakespeare
from src.char_lm import setup_model, setup_training
from src.utils import (
    count_trainable_params, 
    load_config, 
    set_seed, 
    train_and_evaluate_model, 
    evaluate_model, 
    exp_setup,
    log_weight_statistics
)
    

def run(setting, verbose: str=True):
    """ The DL pipeline executor.

    Arguments
    ---------
    setting : dict of dicts
        A hierarchy of dicts that are the arguments for the `setup_model` function.
        It contains a `config` dict for mainly the search space hyperparameters, the 
        subset that changes every run.
        The `fixed_config` dict houses the task related hyperparameters that are less 
        likely to change per run.
        The optional `checkpoint` dict contains necessary information for reloading an 
        existing DL pipeline state saved to disk.
        Note that the `setup_model` modifies and flattens these dicts. Since `config` and
        `fixed_config` could contain the same hyperparameter, the flattening happens with 
        precedence over the `fixed_config` dict values.
    """
    # Setup logger
    wandb_args = dict(project="lm-hpo")
    if "log_name" in setting:
        wandb_args.update(dict(name=setting["log_name"]))
    wandb.init(**wandb_args, config=setting["config"].copy())

    # Set the seed
    set_seed(setting["fixed_config"]["seed"]) 

    # Load defaults
    model, setting = setup_model(**setting)  # setting is now flattened
    if verbose:
        # Print the number of parameters in the model
        print(setting)
        print(count_trainable_params(model)/1e6, 'M parameters')

    # Training setup
    optimizer, scheduler, curr_step, info = setup_training(model, **setting)

    # Training model
    losses = train_and_evaluate_model(
        model=model,
        **setting,
        optimizer=optimizer,
        scheduler=scheduler,
        curr_step=curr_step,
        plot_loss=True,
        info=info,
        # wandb_logger=wandb,
    )

    # Kill logger
    wandb.finish()

    # TODO: log output to return
    return 1     


if __name__ == "__main__":

    d = prepare_shakespeare()

    name = "charLM-test.yaml"
    fixed_setting = exp_setup(f"setup_{name}")

    # adding dataloader as part of experiment setup
    fixed_setting.update(dict(
        vocab_size=d["vocab_size"], 
        dataloader=lambda split, batch_size: get_batch(
            split=split, batch_size=batch_size, block_size=fixed_setting["block_size"],
            train_data=d["train_data"], valid_data=d["valid_data"], 
            device=fixed_setting["device"]
        )
    ))

    config = load_config(name)
    fixed_setting["log_name"] = name

    setting = dict()
    setting.update(dict(
        config=config.copy(),
        fixed_config=fixed_setting,   # important step 
        
    ))
    print("Running an evaluation...")

    run(setting, verbose=True)
# end of file